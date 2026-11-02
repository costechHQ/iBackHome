/// Nigerian time (WAT, UTC+1, no daylight saving). Supervisors and contractors always see WAT
/// (design: "Settings, the same everywhere"), so the phone's own time zone is ignored.
DateTime toWat(DateTime t) => t.toUtc().add(const Duration(hours: 1));

const _days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const _months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

String _two(int n) => n.toString().padLeft(2, '0');

/// `13:24`
String watClock(DateTime t) {
  final w = toWat(t);
  return '${_two(w.hour)}:${_two(w.minute)}';
}

/// `13:24 WAT`
String watTime(DateTime t) => '${watClock(t)} WAT';

/// `Wed 6 Jan`
String watDay(DateTime t) {
  final w = toWat(t);
  return '${_days[w.weekday - 1]} ${w.day} ${_months[w.month - 1]}';
}

/// `Wed 6 Jan, 13:24 WAT`
String watDayTime(DateTime t) => '${watDay(t)}, ${watTime(t)}';

/// `6 Jan` (no weekday), for short lines.
String watShortDate(DateTime t) {
  final w = toWat(t);
  return '${w.day} ${_months[w.month - 1]}';
}
