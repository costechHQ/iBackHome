/// Country and time-zone choices for the profile form. The server checks both; the lists cover where
/// Nigerians abroad and their teams mostly live, and the person's saved value is always kept.
const profileCountries = <String, String>{
  'NG': 'Nigeria',
  'GB': 'United Kingdom',
  'US': 'United States',
  'CA': 'Canada',
  'IE': 'Ireland',
  'DE': 'Germany',
  'FR': 'France',
  'NL': 'Netherlands',
  'IT': 'Italy',
  'ES': 'Spain',
  'SE': 'Sweden',
  'NO': 'Norway',
  'AE': 'United Arab Emirates',
  'SA': 'Saudi Arabia',
  'QA': 'Qatar',
  'ZA': 'South Africa',
  'GH': 'Ghana',
  'KE': 'Kenya',
  'AU': 'Australia',
  'NZ': 'New Zealand',
  'IN': 'India',
  'CN': 'China',
  'SG': 'Singapore',
  'BR': 'Brazil',
};

const profileTimeZones = <String, String>{
  'Africa/Lagos': 'Lagos (WAT)',
  'Africa/Accra': 'Accra (GMT)',
  'Africa/Johannesburg': 'Johannesburg (SAST)',
  'Africa/Nairobi': 'Nairobi (EAT)',
  'Europe/London': 'London',
  'Europe/Dublin': 'Dublin',
  'Europe/Paris': 'Paris',
  'Europe/Berlin': 'Berlin',
  'Europe/Amsterdam': 'Amsterdam',
  'America/New_York': 'New York',
  'America/Chicago': 'Chicago',
  'America/Denver': 'Denver',
  'America/Los_Angeles': 'Los Angeles',
  'America/Toronto': 'Toronto',
  'America/Vancouver': 'Vancouver',
  'Asia/Dubai': 'Dubai',
  'Asia/Riyadh': 'Riyadh',
  'Asia/Kolkata': 'India',
  'Asia/Singapore': 'Singapore',
  'Asia/Shanghai': 'China',
  'Australia/Sydney': 'Sydney',
  'Pacific/Auckland': 'Auckland',
  'UTC': 'UTC',
};

/// The options for a dropdown: the list, plus [current] when it is not already in it.
Map<String, String> withCurrent(Map<String, String> options, String? current) =>
    current == null || current.isEmpty || options.containsKey(current)
    ? options
    : {current: current, ...options};
