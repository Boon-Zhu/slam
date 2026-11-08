# Times describe host request/receipt, not device sample time.
string session_id
string method
uint64 sequence
int64 wall_start_ns
int64 wall_end_ns
uint64 mono_start_ns
uint64 mono_end_ns
SerialChunk[] chunks
# Vendor-decoded values retain vendor order and unverified units.
float64[] values
string text
bool valid
string error
