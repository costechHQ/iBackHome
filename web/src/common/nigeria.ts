// Nigeria's 36 states and the Federal Capital Territory, for site addresses (iBackHome serves projects anywhere
// in Nigeria). Alphabetical, as people look for them.

export const NIGERIAN_STATES = [
  "Abia",
  "Adamawa",
  "Akwa Ibom",
  "Anambra",
  "Bauchi",
  "Bayelsa",
  "Benue",
  "Borno",
  "Cross River",
  "Delta",
  "Ebonyi",
  "Edo",
  "Ekiti",
  "Enugu",
  "FCT (Abuja)",
  "Gombe",
  "Imo",
  "Jigawa",
  "Kaduna",
  "Kano",
  "Katsina",
  "Kebbi",
  "Kogi",
  "Kwara",
  "Lagos",
  "Nasarawa",
  "Niger",
  "Ogun",
  "Ondo",
  "Osun",
  "Oyo",
  "Plateau",
  "Rivers",
  "Sokoto",
  "Taraba",
  "Yobe",
  "Zamfara",
] as const;

/** "12 Chime Avenue, New Haven, Enugu State"; the FCT reads as it is. */
export function siteAddress(street: string, town: string, state: string): string {
  const region = state.startsWith("FCT") ? state : `${state} State`;
  return [street.trim(), town.trim(), region].filter(Boolean).join(", ");
}
