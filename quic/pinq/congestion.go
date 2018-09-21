/*
Package minq is a minimal implementation of QUIC, as documented at
https://quicwg.github.io/. Minq partly implements draft-04.

*/
package minq

import (
	"math"
	"time"
//	"fmt"
)

// congestion control related constants
const (
	kDefaultMss            = 1460   // bytes
	kInitalWindow          = 10 * kDefaultMss
	kMinimumWindow         =  2 * kDefaultMss
	kMaximumWindow         = kInitalWindow
	kLossReductionFactor   = 0.5
)

// loss dectection related constants
const (
	kMaxTLPs                 = 2
	kReorderingThreshold     = 3
	kTimeReorderingFraction  = 0.125
	kMinTLPTimeout           = 10   // ms
	kMinRTOTimeout           = 200  // ms
	kDelayedAckTimeout       = 25   // ms
//	kDefaultInitialRtt       = 100  // ms // already in connection.go
)

type CongestionController interface {
	onPacketSent(pn uint64, isAckOnly bool, sentBytes int)
	onAckReceived(acks ackRanges, delay time.Duration)
	bytesAllowedToSend() int
	setLostPacketHandler(handler func(pn uint64))
	checkLossDetectionAlarm()
}

/*
 * DUMMY congestion controller
 */

type CongestionControllerDummy struct{

}

func (cc *CongestionControllerDummy) onPacketSent(pn uint64, isAckOnly bool, sentBytes int){
}

func (cc *CongestionControllerDummy) onAckReceived(acks ackRanges, delay time.Duration){
}

func (cc *CongestionControllerDummy) bytesAllowedToSend() int{
	/* return the the maximum int value */
	return int(^uint(0) >> 1)
}

func (cc *CongestionControllerDummy) checkLossDetectionAlarm(){
}


//////////////////////////////////////////////
///////////////////////////////////////////////
////////////////////////////////////////////

/*
 * FIXED RATE congestion controller
 * Yeah yeah, I know, it's not a congestion controller.
 */

type CongestionControllerFixedRate struct {
	// Congestion control related
	startTime               time.Time
	rate                    float64      // packets / min
	initialCredit           int
	transmitted             int

	// Loss detection related
	timeOfLastSentPacket    time.Time
	largestSendPacket       uint64
	largestAckedPacket      uint64
	smoothedRtt             time.Duration
	rttVar                  time.Duration
	smoothedRttTcp          time.Duration
	rttVarTcp               time.Duration
	reorderingThreshold     int
	timeReorderingFraction  float32
	lossTime                time.Time
	sentPackets             map[uint64]packetEntry

	// others
	lostPacketHandler       func(pn uint64)
	conn                    *Connection
}

func (cc *CongestionControllerFixedRate) onPacketSent(pn uint64, isAckOnly bool, sentBytes int){
	cc.timeOfLastSentPacket = time.Now()
	cc.largestSendPacket = pn
	packetData := packetEntry{pn, time.Now(), 0}
	cc.conn.log(logTypeCongestion, "Packet send pn: %d len:%d ackonly: %v\n", pn, sentBytes, isAckOnly)
	if !isAckOnly{
		cc.onPacketSentCC(sentBytes)
		packetData.bytes = sentBytes
	}
	cc.sentPackets[pn] = packetData
}

// acks is received to be a sorted list, where the largest packet numbers are at the beginning
func(cc *CongestionControllerFixedRate) onAckReceived(acks ackRanges, ackDelay time.Duration){

	// keep track of largest packet acked overall
	if acks[0].lastPacket > cc.largestAckedPacket {
		cc.largestAckedPacket = acks[0].lastPacket
	}

	// If the largest acked is newly acked update rtt
	_, present := cc.sentPackets[acks[0].lastPacket]
	if present {
		latestRtt := time.Since(cc.sentPackets[acks[0].lastPacket].txTime)
		cc.conn.log(logTypeCongestion, "latestRtt: %v, ackDelay: %v", latestRtt, ackDelay)
		cc.updateRttTcp(latestRtt)

		if (latestRtt > ackDelay && ackDelay > 0){
			latestRtt -= ackDelay
		}
		cc.updateRtt(latestRtt)
	}

	// find and proccess newly acked packets
	for _, ackBlock := range acks {
		for pn := ackBlock.lastPacket; pn > (ackBlock.lastPacket - ackBlock.count); pn-- {
			cc.conn.log(logTypeCongestion, "Ack for pn %d received", pn)
			_, present := cc.sentPackets[pn]
			if present {
				cc.conn.log(logTypeCongestion, "First ack for pn %d received", pn)
				cc.onPacketAcked(pn)
			}
		}
	}

	cc.detectLostPackets()
}

func (cc *CongestionControllerFixedRate)	setLostPacketHandler(handler func(pn uint64)){
	cc.lostPacketHandler = handler
}


func(cc *CongestionControllerFixedRate) updateRtt(latestRtt time.Duration){
	if (cc.smoothedRtt == 0){
		cc.smoothedRtt = latestRtt
		cc.rttVar = time.Duration(int64(latestRtt) / 2)
	} else {
		rttDelta := cc.smoothedRtt - latestRtt;
		if rttDelta < 0 {
			rttDelta = -rttDelta
		}
		cc.rttVar = time.Duration(int64(cc.rttVar) * 3/4 + int64(rttDelta) * 1/4)
		cc.smoothedRtt = time.Duration(int64(cc.smoothedRtt) * 7/8 + int64(latestRtt) * 1/8)
	}
	cc.conn.log(logTypeCongestion, "New RTT estimate: %v, variance: %v", cc.smoothedRtt, cc.rttVar)

	variance := float64(cc.rttVar) / float64(time.Millisecond)
	rtt := float64(cc.smoothedRtt) / float64(time.Millisecond)
	logf(logTypeStatistic, "RTT: time: %f variance: %f rtt: %f",
		 float64(time.Now().UnixNano()) / 1e9, variance, rtt)
}

func(cc *CongestionControllerFixedRate) updateRttTcp(latestRtt time.Duration){
	if (cc.smoothedRttTcp == 0){
		cc.smoothedRttTcp = latestRtt
		cc.rttVarTcp = time.Duration(int64(latestRtt) / 2)
	} else {
		rttDelta := cc.smoothedRttTcp - latestRtt;
		if rttDelta < 0 {
			rttDelta = -rttDelta
		}
		cc.rttVarTcp = time.Duration(int64(cc.rttVarTcp) * 3/4 + int64(rttDelta) * 3/4)
		cc.smoothedRttTcp = time.Duration(int64(cc.smoothedRttTcp) * 7/8 + int64(latestRtt) * 1/8)
	}
	cc.conn.log(logTypeCongestion, "New RTT(TCP) estimate: %v, variance: %v", cc.smoothedRttTcp, cc.rttVarTcp)

	variance := float64(cc.rttVarTcp) / float64(time.Millisecond)
	rtt := float64(cc.smoothedRttTcp) / float64(time.Millisecond)
	logf(logTypeStatistic, "RTT_TCP: time: %f variance: %f rtt: %f",
		 float64(time.Now().UnixNano()) / 1e9, variance, rtt)
}


func(cc *CongestionControllerFixedRate) onPacketAcked(pn uint64){
	rtt := float64(time.Since(cc.sentPackets[pn].txTime))/float64(time.Millisecond) // [ms]
	logf(logTypeStatistic, "ACK_DELAY: pn: %d time: %f rtt: %f",
		 pn, float64(time.Now().UnixNano()) / 1e9, rtt)
	cc.onPacketAckedCC(pn)
	//TODO(ekr@rtfm.com) some RTO stuff here
	delete(cc.sentPackets, pn)
}

func(cc *CongestionControllerFixedRate) checkLossDetectionAlarm(){
}

func(cc *CongestionControllerFixedRate) detectLostPackets(){
	var lostPackets []packetEntry
	//TODO(ekr@rtfm.com) implement loss detection different from reorderingThreshold
	for _, packet := range cc.sentPackets {
		if (cc.largestAckedPacket > packet.pn) &&
			(cc.largestAckedPacket - packet.pn > uint64(cc.reorderingThreshold)) {
				lostPackets = append(lostPackets, packet)
		}
	}

	if len(lostPackets) > 0{
		cc.onPacketsLost(lostPackets)
	}
	for _, packet := range lostPackets {
		delete(cc.sentPackets, packet.pn)
	}
}

func (cc *CongestionControllerFixedRate) onPacketSentCC(bytes_sent int){
	cc.transmitted += bytes_sent
}

func (cc *CongestionControllerFixedRate) onPacketAckedCC(pn uint64){
}

func (cc *CongestionControllerFixedRate) onPacketsLost(packets []packetEntry){
	for _, packet := range packets {

		// First remove lost packets from bytesInFlight and inform the connection
		// of the loss
		cc.conn.log(logTypeCongestion, "Packet pn: %d len: %d is lost", packet.pn, packet.bytes)
		if cc.lostPacketHandler != nil {
			cc.lostPacketHandler(packet.pn)
		}
	}

	// Tell the measurement system, so we can set the loss bit
	cc.conn.measurement.lossMeasurementTasks()
}

func (cc *CongestionControllerFixedRate) bytesAllowedToSend() int {
	secondsSinceStart := time.Since(cc.startTime).Seconds()
	credit := int(cc.rate * secondsSinceStart) + cc.initialCredit

	allowance := credit - cc.transmitted

	/* round off to number of packets allowed */
	if allowance > 0 {
		allowance = allowance - (allowance % kDefaultMss)
	}

	return allowance
}

func newCongestionControllerFixedRate(conn *Connection, rate float64, initialCredit int) *CongestionControllerFixedRate{
	return &CongestionControllerFixedRate{
		time.Now(),                      // startTime
		rate,                            // rate
		initialCredit,                   // initialCredit
		0,                               // transmitted
		time.Unix(0,0),                  // timeOfLastSentPacket
		0,                               // largestSendPacket
		0,                               // largestAckedPacket
		0,                               // smoothedRtt
		0,                               // rttVar
		0,                               // smoothedRttTcp
		0,                               // rttVarTcp
		kReorderingThreshold,            // reorderingThreshold
		math.MaxFloat32,                 // timeReorderingFraction
		time.Unix(0,0),                  // lossTime
		make(map[uint64]packetEntry),    // sentPackets
		nil,                             // lostPacketHandler
		conn,                            // conn
	}
}



////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////




/*
 * FIXED WINDOW congestion controller
 * Yeah yeah, I know, it's not a congestion controller.
 */

type CongestionControllerFixedWindow struct {
	// Congestion control related
	bytesInFlight           int
	congestionWindow        int
	congestionWindowDefault int
	endOfRecovery           uint64
	sstresh                 int
	bytesRxInRecovery       int
	bytesTxInRecovery       int

	// Loss detection related
	lossDetectionAlarm      time.Time //TODO(ekr@rtfm.com) set this to the right type
	handshakeCount          int
	tlpCount                int
	rtoCount                int
	largestSendBeforeRto    uint64
	timeOfLastSentPacket    time.Time
	largestSendPacket       uint64
	largestAckedPacket      uint64
//	largestRtt              time.Duration
	smoothedRtt             time.Duration
	rttVar                  time.Duration
	smoothedRttTcp          time.Duration
	rttVarTcp               time.Duration
	reorderingThreshold     int
	timeReorderingFraction  float32
	lossTime                time.Time
	sentPackets             map[uint64]packetEntry

	// others
	lostPacketHandler       func(pn uint64)
	conn                    *Connection
}

func (cc *CongestionControllerFixedWindow) onPacketSent(pn uint64, isAckOnly bool, sentBytes int){
	cc.timeOfLastSentPacket = time.Now()
	cc.largestSendPacket = pn
	packetData := packetEntry{pn, time.Now(), 0}
	cc.conn.log(logTypeCongestion, "Packet send pn: %d len:%d ackonly: %v\n", pn, sentBytes, isAckOnly)
	if !isAckOnly{
		cc.onPacketSentCC(sentBytes)
		packetData.bytes = sentBytes
		cc.setLossDetectionAlarm()
	}
	cc.sentPackets[pn] = packetData
}

// acks is received to be a sorted list, where the largest packet numbers are at the beginning
func(cc *CongestionControllerFixedWindow) onAckReceived(acks ackRanges, ackDelay time.Duration){

	// keep track of largest packet acked overall
	if acks[0].lastPacket > cc.largestAckedPacket {
		cc.largestAckedPacket = acks[0].lastPacket
	}

	// If the largest acked is newly acked update rtt
	_, present := cc.sentPackets[acks[0].lastPacket]
	if present {
		latestRtt := time.Since(cc.sentPackets[acks[0].lastPacket].txTime)
		cc.conn.log(logTypeCongestion, "latestRtt: %v, ackDelay: %v", latestRtt, ackDelay)
		cc.updateRttTcp(latestRtt)

		if (latestRtt > ackDelay && ackDelay > 0){
			latestRtt -= ackDelay
		}
		cc.updateRtt(latestRtt)
	}

	// find and proccess newly acked packets
	for _, ackBlock := range acks {
		for pn := ackBlock.lastPacket; pn > (ackBlock.lastPacket - ackBlock.count); pn-- {
			cc.conn.log(logTypeCongestion, "Ack for pn %d received", pn)
			_, present := cc.sentPackets[pn]
			if present {
				cc.conn.log(logTypeCongestion, "First ack for pn %d received", pn)
				cc.onPacketAcked(pn)
			}
		}
	}

	cc.detectLostPackets()
	cc.setLossDetectionAlarm()
}

func (cc *CongestionControllerFixedWindow)	setLostPacketHandler(handler func(pn uint64)){
	cc.lostPacketHandler = handler
}


func(cc *CongestionControllerFixedWindow) updateRtt(latestRtt time.Duration){
	if (cc.smoothedRtt == 0){
		cc.smoothedRtt = latestRtt
		cc.rttVar = time.Duration(int64(latestRtt) / 2)
	} else {
		rttDelta := cc.smoothedRtt - latestRtt;
		if rttDelta < 0 {
			rttDelta = -rttDelta
		}
		cc.rttVar = time.Duration(int64(cc.rttVar) * 3/4 + int64(rttDelta) * 1/4)
		cc.smoothedRtt = time.Duration(int64(cc.smoothedRtt) * 7/8 + int64(latestRtt) * 1/8)
	}
	cc.conn.log(logTypeCongestion, "New RTT estimate: %v, variance: %v", cc.smoothedRtt, cc.rttVar)

	variance := float64(cc.rttVar) / float64(time.Millisecond)
	rtt := float64(cc.smoothedRtt) / float64(time.Millisecond)
	logf(logTypeStatistic, "RTT: time: %f variance: %f rtt: %f",
		 float64(time.Now().UnixNano()) / 1e9, variance, rtt)
}

func(cc *CongestionControllerFixedWindow) updateRttTcp(latestRtt time.Duration){
	if (cc.smoothedRttTcp == 0){
		cc.smoothedRttTcp = latestRtt
		cc.rttVarTcp = time.Duration(int64(latestRtt) / 2)
	} else {
		rttDelta := cc.smoothedRttTcp - latestRtt;
		if rttDelta < 0 {
			rttDelta = -rttDelta
		}
		cc.rttVarTcp = time.Duration(int64(cc.rttVarTcp) * 3/4 + int64(rttDelta) * 3/4)
		cc.smoothedRttTcp = time.Duration(int64(cc.smoothedRttTcp) * 7/8 + int64(latestRtt) * 1/8)
	}
	cc.conn.log(logTypeCongestion, "New RTT(TCP) estimate: %v, variance: %v", cc.smoothedRttTcp, cc.rttVarTcp)

	variance := float64(cc.rttVarTcp) / float64(time.Millisecond)
	rtt := float64(cc.smoothedRttTcp) / float64(time.Millisecond)
	logf(logTypeStatistic, "RTT_TCP: time: %f variance: %f rtt: %f",
		 float64(time.Now().UnixNano()) / 1e9, variance, rtt)
}


func(cc *CongestionControllerFixedWindow) onPacketAcked(pn uint64){
	rtt := float64(time.Since(cc.sentPackets[pn].txTime))/float64(time.Millisecond) // [ms]
	logf(logTypeStatistic, "ACK_DELAY: pn: %d time: %f rtt: %f",
		 pn, float64(time.Now().UnixNano()) / 1e9, rtt)
	cc.onPacketAckedCC(pn)
	//TODO(ekr@rtfm.com) some RTO stuff here
	cc.congestionWindow = cc.congestionWindowDefault
	delete(cc.sentPackets, pn)
}

func(cc *CongestionControllerFixedWindow) setLossDetectionAlarm(){
	//TODO(piet@devae.re) check if handshake done
	//TODO(piet@devae.re) At the moment only does Tail Loss Probes, no RTO

	/* If there is nothing that we can retransmit ... */
	if (cc.bytesInFlight == 0){
		cc.lossDetectionAlarm = time.Unix(0,0)
		return
	}

	alarm_duration := time.Duration(1.5 * float32(cc.smoothedRtt));
	if (alarm_duration < kMinTLPTimeout * time.Millisecond) {
		alarm_duration = kMinTLPTimeout
	}

	cc.lossDetectionAlarm = cc.timeOfLastSentPacket.Add(alarm_duration);
}

func(cc *CongestionControllerFixedWindow) checkLossDetectionAlarm(){
	if (cc.lossDetectionAlarm != time.Unix(0,0) &&
			time.Now().After(cc.lossDetectionAlarm)){
		cc.onLossDetectionAlarm()
	}
}

func(cc *CongestionControllerFixedWindow) onLossDetectionAlarm(){
	/* Derives from the draft-ietf-quic-recovery */

	logf(logTypeStatistic, "LOSS_DETECTION_ALARM: time: %f",
		 float64(time.Now().UnixNano()) / 1e9)

	/* only doing a TLP probe at the moment,
	   actual transmission will be done by connection.CheckTimer()
	*/
	cc.congestionWindow += kDefaultMss
	logf(logTypeStatistic, "CONGESTION_WINDOW time: %f bytes: %d",
		 float64(time.Now().UnixNano()) / 1e9, cc.congestionWindow)

	cc.setLossDetectionAlarm()
}

func(cc *CongestionControllerFixedWindow) detectLostPackets(){
	var lostPackets []packetEntry
	//TODO(ekr@rtfm.com) implement loss detection different from reorderingThreshold
	for _, packet := range cc.sentPackets {
		if (cc.largestAckedPacket > packet.pn) &&
			(cc.largestAckedPacket - packet.pn > uint64(cc.reorderingThreshold)) {
				lostPackets = append(lostPackets, packet)
		}
	}

	if len(lostPackets) > 0{
		cc.onPacketsLost(lostPackets)
	}
	for _, packet := range lostPackets {
		delete(cc.sentPackets, packet.pn)
	}
}

func (cc *CongestionControllerFixedWindow) onPacketSentCC(bytes_sent int){

	// if we are in recovery
	if cc.largestAckedPacket < cc.endOfRecovery {
		cc.bytesTxInRecovery += bytes_sent
		cc.conn.log(logTypeCongestion, "%d bytes transmitted while in recovery. Totaling: %d", bytes_sent,  cc.bytesTxInRecovery)
	}

	cc.bytesInFlight += bytes_sent
	logf(logTypeStatistic, "BYTES_IN_FLIGHT time: %f bytes: %d",
		 float64(time.Now().UnixNano()) / 1e9, cc.bytesInFlight)
	cc.conn.log(logTypeCongestion, "%d bytes added to bytesInFlight", bytes_sent)
}

func (cc *CongestionControllerFixedWindow) onPacketAckedCC(pn uint64){
	cc.bytesInFlight -= cc.sentPackets[pn].bytes
	logf(logTypeStatistic, "BYTES_IN_FLIGHT time: %f bytes: %d",
		 float64(time.Now().UnixNano()) / 1e9,  cc.bytesInFlight)
	cc.conn.log(logTypeCongestion, "%d bytes from packet %d removed from bytesInFlight", cc.sentPackets[pn].bytes, pn)
}

func (cc *CongestionControllerFixedWindow) onPacketsLost(packets []packetEntry){
	var largestLostPn uint64 = 0
	for _, packet := range packets {

		// First remove lost packets from bytesInFlight and inform the connection
		// of the loss
		cc.conn.log(logTypeCongestion, "Packet pn: %d len: %d is lost", packet.pn, packet.bytes)
		cc.bytesInFlight -= packet.bytes
		if cc.lostPacketHandler != nil {
			cc.lostPacketHandler(packet.pn)
		}

		// and keep track of the largest lost packet
		if packet.pn > largestLostPn {
			largestLostPn = packet.pn
		}
	}

	// Tell the measurement system, so we can set the loss bit
	cc.conn.measurement.lossMeasurementTasks()
}

func (cc *CongestionControllerFixedWindow) bytesAllowedToSend() int {
	logf(logTypeStatistic, "BYTES_ALLOWED_TO_SEMND time: %f bytes: %d",
		 float64(time.Now().UnixNano()) / 1e9, cc.congestionWindow - cc.bytesInFlight)
	return cc.congestionWindow - cc.bytesInFlight
}

func newCongestionControllerFixedWindow(conn *Connection, windowSize int) *CongestionControllerFixedWindow{
	return &CongestionControllerFixedWindow{
		0,                             // bytesInFlight
		windowSize,                    // congestionWindow
		windowSize,                    // congestionWindowDefault
		0,                             // endOfRecovery
		int(^uint(0) >> 1),            // sstresh
		0,                             // bytesRxInRecovery
		0,                             // bytesTxInRecovery
		time.Unix(0,0),                // lossDetectionAlarm
		0,                             // handshakeCount
		0,                             // tlpCount
		0,                             // rtoCount
		0,                             // largestSendBeforeRto
		time.Unix(0,0),                // timeOfLastSentPacket
		0,                             // largestSendPacket
		0,                             // largestAckedPacket
		0,                             // smoothedRtt
		0,                             // rttVar
		0,                             // smoothedRttTcp
		0,                             // rttVarTcp
		kReorderingThreshold,          // reorderingThreshold
		math.MaxFloat32,               // timeReorderingFraction
		time.Unix(0,0),                // lossTime
		make(map[uint64]packetEntry),  // sentPackets
		nil,                           // lostPacketHandler
		conn,                          // conn
	}
}

/*
 * draft-ietf-quic-recovery congestion controller
 */

type CongestionControllerIetf struct {
	// Congestion control related
	bytesInFlight          int
	congestionWindow       int
	endOfRecovery          uint64
	sstresh                int
	bytesRxInRecovery      int
	bytesTxInRecovery      int

	// Loss detection related
	lossDetectionAlarm     time.Time
	handshakeCount         int
	tlpCount               int
	rtoCount               int
	largestSendBeforeRto   uint64
	timeOfLastSentPacket   time.Time
	largestSendPacket      uint64
	largestAckedPacket     uint64
//	largestRtt             time.Duration
	smoothedRtt            time.Duration
	rttVar                 time.Duration
	smoothedRttTcp         time.Duration
	rttVarTcp              time.Duration
	reorderingThreshold    int
	timeReorderingFraction float32
	lossTime               time.Time
	sentPackets            map[uint64]packetEntry

	// others
	lostPacketHandler      func(pn uint64)
	conn                   *Connection
}

type packetEntry struct{
	pn         uint64
	txTime     time.Time
	bytes      int
}


func (cc *CongestionControllerIetf) onPacketSent(pn uint64, isAckOnly bool, sentBytes int){
	cc.timeOfLastSentPacket = time.Now()
	cc.largestSendPacket = pn
	packetData := packetEntry{pn, time.Now(), 0}
	cc.conn.log(logTypeCongestion, "Packet send pn: %d len:%d ackonly: %v\n", pn, sentBytes, isAckOnly)
	if !isAckOnly{
		cc.onPacketSentCC(sentBytes)
		packetData.bytes = sentBytes
		cc.setLossDetectionAlarm()
	}
	cc.sentPackets[pn] = packetData
}


// acks is received to be a sorted list, where the largest packet numbers are at the beginning
func(cc *CongestionControllerIetf) onAckReceived(acks ackRanges, ackDelay time.Duration){

	// keep track of largest packet acked overall
	if acks[0].lastPacket > cc.largestAckedPacket {
		cc.largestAckedPacket = acks[0].lastPacket
	}

	// If the largest acked is newly acked update rtt
	_, present := cc.sentPackets[acks[0].lastPacket]
	if present {
		latestRtt := time.Since(cc.sentPackets[acks[0].lastPacket].txTime)
		cc.conn.log(logTypeCongestion, "latestRtt: %v, ackDelay: %v", latestRtt, ackDelay)
		cc.updateRttTcp(latestRtt)

		if (latestRtt > ackDelay && ackDelay > 0){
			latestRtt -= ackDelay
		}
		cc.updateRtt(latestRtt)
	}

	// find and proccess newly acked packets
	for _, ackBlock := range acks {
		for pn := ackBlock.lastPacket; pn > (ackBlock.lastPacket - ackBlock.count); pn-- {
			cc.conn.log(logTypeCongestion, "Ack for pn %d received", pn)
			_, present := cc.sentPackets[pn]
			if present {
				cc.conn.log(logTypeCongestion, "First ack for pn %d received", pn)
				cc.onPacketAcked(pn)
			}
		}
	}

	cc.detectLostPackets()
	cc.setLossDetectionAlarm()
}

func (cc *CongestionControllerIetf)	setLostPacketHandler(handler func(pn uint64)){
	cc.lostPacketHandler = handler
}


func(cc *CongestionControllerIetf) updateRtt(latestRtt time.Duration){
	if (cc.smoothedRtt == 0){
		cc.smoothedRtt = latestRtt
		cc.rttVar = time.Duration(int64(latestRtt) / 2)
	} else {
		rttDelta := cc.smoothedRtt - latestRtt;
		if rttDelta < 0 {
			rttDelta = -rttDelta
		}
		cc.rttVar = time.Duration(int64(cc.rttVar) * 3/4 + int64(rttDelta) * 1/4)
		cc.smoothedRtt = time.Duration(int64(cc.smoothedRtt) * 7/8 + int64(latestRtt) * 1/8)
	}
	cc.conn.log(logTypeCongestion, "New RTT estimate: %v, variance: %v", cc.smoothedRtt, cc.rttVar)

	variance := float64(cc.rttVar) / float64(time.Millisecond)
	rtt := float64(cc.smoothedRtt) / float64(time.Millisecond)
	logf(logTypeStatistic, "RTT: time: %f variance: %f rtt: %f",
		 float64(time.Now().UnixNano()) / 1e9, variance, rtt)
}

func(cc *CongestionControllerIetf) updateRttTcp(latestRtt time.Duration){
	if (cc.smoothedRttTcp == 0){
		cc.smoothedRttTcp = latestRtt
		cc.rttVarTcp = time.Duration(int64(latestRtt) / 2)
	} else {
		rttDelta := cc.smoothedRttTcp - latestRtt;
		if rttDelta < 0 {
			rttDelta = -rttDelta
		}
		cc.rttVarTcp = time.Duration(int64(cc.rttVarTcp) * 3/4 + int64(rttDelta) * 3/4)
		cc.smoothedRttTcp = time.Duration(int64(cc.smoothedRttTcp) * 7/8 + int64(latestRtt) * 1/8)
	}
	cc.conn.log(logTypeCongestion, "New RTT(TCP) estimate: %v, variance: %v", cc.smoothedRttTcp, cc.rttVarTcp)

	variance := float64(cc.rttVarTcp) / float64(time.Millisecond)
	rtt := float64(cc.smoothedRttTcp) / float64(time.Millisecond)
	logf(logTypeStatistic, "RTT_TCP: time: %f variance: %f rtt: %f",
		 float64(time.Now().UnixNano()) / 1e9, variance, rtt)
}


func(cc *CongestionControllerIetf) onPacketAcked(pn uint64){
	rtt := float64(time.Since(cc.sentPackets[pn].txTime))/float64(time.Millisecond) // [ms]
	logf(logTypeStatistic, "ACK_DELAY: pn: %d time: %f rtt: %f",
		 pn, float64(time.Now().UnixNano()) / 1e9, rtt)
	cc.onPacketAckedCC(pn)
	//TODO(ekr@rtfm.com) some RTO stuff here
	delete(cc.sentPackets, pn)
}

func(cc *CongestionControllerIetf) setLossDetectionAlarm(){
	//TODO(piet@devae.re) check if handshake done
	//TODO(piet@devae.re) At the moment only does Tail Loss Probes, no RTO

	/* If there is nothing that we can retransmit ... */
	if (cc.bytesInFlight == 0){
		cc.lossDetectionAlarm = time.Unix(0,0)
		return
	}

	alarm_duration := time.Duration(1.5 * float32(cc.smoothedRtt));
	if (alarm_duration < kMinTLPTimeout * time.Millisecond) {
		alarm_duration = kMinTLPTimeout
	}

	cc.lossDetectionAlarm = cc.timeOfLastSentPacket.Add(alarm_duration);
}

func(cc *CongestionControllerIetf) checkLossDetectionAlarm(){
	if (cc.lossDetectionAlarm != time.Unix(0,0) &&
			time.Now().After(cc.lossDetectionAlarm)){
		cc.onLossDetectionAlarm()
	}
}

func(cc *CongestionControllerIetf) onLossDetectionAlarm(){
	/* Derives from the draft-ietf-quic-recovery */

	logf(logTypeStatistic, "LOSS_DETECTION_ALARM: time: %f",
		 float64(time.Now().UnixNano()) / 1e9)

	/* only doing a TLP probe at the moment,
	   actual transmission will be done by connection.CheckTimer()
	*/
	cc.congestionWindow += kDefaultMss
	logf(logTypeStatistic, "CONGESTION_WINDOW time: %f bytes: %d",
		 float64(time.Now().UnixNano()) / 1e9, cc.congestionWindow)

	cc.setLossDetectionAlarm()
}

func(cc *CongestionControllerIetf) detectLostPackets(){
	var lostPackets []packetEntry
	//TODO(ekr@rtfm.com) implement loss detection different from reorderingThreshold
	for _, packet := range cc.sentPackets {
		if (cc.largestAckedPacket > packet.pn) &&
			(cc.largestAckedPacket - packet.pn > uint64(cc.reorderingThreshold)) {
				lostPackets = append(lostPackets, packet)
		}
	}

	if len(lostPackets) > 0{
		cc.onPacketsLost(lostPackets)
	}
	for _, packet := range lostPackets {
		delete(cc.sentPackets, packet.pn)
	}
}

func (cc *CongestionControllerIetf) onPacketSentCC(bytes_sent int){

	// if we are in recovery
	if cc.largestAckedPacket < cc.endOfRecovery {
		cc.bytesTxInRecovery += bytes_sent
		cc.conn.log(logTypeCongestion, "%d bytes transmitted while in recovery. Totaling: %d", bytes_sent,  cc.bytesTxInRecovery)
	}

	cc.bytesInFlight += bytes_sent
	logf(logTypeStatistic, "BYTES_IN_FLIGHT time: %f bytes: %d",
		 float64(time.Now().UnixNano()) / 1e9, cc.bytesInFlight)
	cc.conn.log(logTypeCongestion, "%d bytes added to bytesInFlight", bytes_sent)
}

func (cc *CongestionControllerIetf) onPacketAckedCC(pn uint64){
	cc.bytesInFlight -= cc.sentPackets[pn].bytes
	logf(logTypeStatistic, "BYTES_IN_FLIGHT time: %f bytes: %d",
		 float64(time.Now().UnixNano()) / 1e9,  cc.bytesInFlight)
	cc.conn.log(logTypeCongestion, "%d bytes from packet %d removed from bytesInFlight", cc.sentPackets[pn].bytes, pn)

	// if we are in recovery mode
	if pn < cc.endOfRecovery {
		cc.bytesRxInRecovery += cc.sentPackets[pn].bytes
		cc.conn.log(logTypeCongestion, "%d bytes recieved while in recovery. Totaling: %d", cc.sentPackets[pn].bytes,  cc.bytesRxInRecovery)
		return
	}
	if cc.congestionWindow < cc.sstresh {
		// Slow start
		cc.congestionWindow += cc.sentPackets[pn].bytes
		cc.conn.log(logTypeCongestion, "PDV Slow Start: increasing window size with %d bytes to %d",
				cc.sentPackets[pn].bytes, cc.congestionWindow)
	} else {

		// Congestion avoidance
		cc.congestionWindow += kDefaultMss * cc.sentPackets[pn].bytes / cc.congestionWindow
		cc.conn.log(logTypeCongestion, "PDV Congestion Avoidance: increasing window size to %d",
			cc.congestionWindow)
	}
	logf(logTypeStatistic, "CONGESTION_WINDOW time: %f bytes: %d",
		 float64(time.Now().UnixNano()) / 1e9, cc.congestionWindow)
}

func (cc *CongestionControllerIetf) onPacketsLost(packets []packetEntry){
	var largestLostPn uint64 = 0
	for _, packet := range packets {

		// First remove lost packets from bytesInFlight and inform the connection
		// of the loss
		cc.conn.log(logTypeCongestion, "Packet pn: %d len: %d is lost", packet.pn, packet.bytes)
		logf(logTypeStatistic, "LOST_PACKET: time: %f pn: %d",
		 float64(time.Now().UnixNano()) / 1e9, packet.pn)
		cc.bytesInFlight -= packet.bytes
		if cc.lostPacketHandler != nil {
			cc.lostPacketHandler(packet.pn)
		}

		// and keep track of the largest lost packet
		if packet.pn > largestLostPn {
			largestLostPn = packet.pn
		}

	}

	// Now start a new recovery epoch if the largest lost packet is larger than the
	// end of the previous recovery epoch
	if cc.endOfRecovery < largestLostPn {
		cc.endOfRecovery = cc.largestSendPacket
		cc.bytesRxInRecovery = 0
		cc.bytesTxInRecovery = 0
		cc.congestionWindow = int(float32(cc.congestionWindow) * kLossReductionFactor)
		if kMinimumWindow > cc.congestionWindow {
			cc.congestionWindow = kMinimumWindow
		}
		logf(logTypeStatistic, "CONGESTION_WINDOW time: %f bytes: %d",
			 float64(time.Now().UnixNano()) / 1e9, cc.congestionWindow)
		cc.sstresh = cc.congestionWindow
		cc.conn.log(logTypeCongestion, "PDV Recovery started. Window size: %d, sstresh: %d, endOfRecovery %d",
					cc.congestionWindow, cc.sstresh, cc.endOfRecovery)
	}

	// Tell the measurement system, so we can set the loss bit
	cc.conn.measurement.lossMeasurementTasks()
}

func (cc *CongestionControllerIetf) bytesAllowedToSend() int {
	// if we are in recovery mode
	if cc.largestAckedPacket < cc.endOfRecovery {
		fastRecoveryAllowance := ( cc.bytesRxInRecovery / 2 ) - cc.bytesTxInRecovery
		cwindAllowance := cc.congestionWindow - cc.bytesInFlight

		cc.conn.log(logTypeCongestion, "Bytes allowed To Send by fast ecovery: %d / 2 - %d = %d", cc.bytesRxInRecovery, cc.bytesTxInRecovery, fastRecoveryAllowance)
		cc.conn.log(logTypeCongestion, "Bytes allowed To Send by cwind: %d", cwindAllowance)

		if fastRecoveryAllowance > cwindAllowance {
			return fastRecoveryAllowance
		} else {
			return cwindAllowance
		}

	} else {
		//cc.conn.log(logTypeCongestion, "Remaining congestion window size: %d", cc.congestionWindow - cc.bytesInFlight)
		return cc.congestionWindow - cc.bytesInFlight
	}
}

func newCongestionControllerIetf(conn *Connection) *CongestionControllerIetf{
	return &CongestionControllerIetf{
		0,                             // bytesInFlight
		kInitalWindow,                 // congestionWindow
		0,                             // endOfRecovery
		int(^uint(0) >> 1),            // sstresh
		0,                             // bytesRxInRecovery
		0,                             // bytesTxInRecovery
		time.Unix(0,0),                // lossDetectionAlarm
		0,                             // handshakeCount
		0,                             // tlpCount
		0,                             // rtoCount
		0,                             // largestSendBeforeRto
		time.Unix(0,0),                // timeOfLastSentPacket
		0,                             // largestSendPacket
		0,                             // largestAckedPacket
		0,                             // smoothedRtt
		0,                             // rttVar
		0,                             // smoothedRttTcp
		0,                             // rttVarTcp
		kReorderingThreshold,          // reorderingThreshold
		math.MaxFloat32,               // timeReorderingFraction
		time.Unix(0,0),                // lossTime
		make(map[uint64]packetEntry),  // sentPackets
		nil,                           // lostPacketHandler
		conn,                          // conn
	}
}

