// Landing-page photography: free-licence stock from Pexels, resized by hand into public/landing/. These are
// illustrations of Nigerian homes and building sites, not iBackHome customers' projects, and the pages say so.
// Every photo has a place only where its Pexels caption gives one.

export type Photo = { src: string; width: number; height: number; alt: string; place?: string };

const photo = (name: string, width: number, height: number, alt: string, place?: string): Photo => ({
  src: `/landing/${name}.jpg`,
  width,
  height,
  alt,
  place,
});

export const PHOTOS = {
  abujaBungalow: photo(
    "abuja-bungalow",
    1400,
    935,
    "A blue and white bungalow with arched doorways, palm trees and a trimmed hedge.",
    "Abuja",
  ),
  abujaHouse: photo(
    "abuja-house",
    900,
    1350,
    "A finished three-storey house with a brick feature wall, balconies and a boundary fence.",
    "Abuja",
  ),
  enuguAerial: photo(
    "enugu-aerial",
    1400,
    754,
    "An aerial view of Enugu: red roofs among trees and a lake at dusk.",
    "Enugu",
  ),
  abujaZumaRock: photo(
    "abuja-zuma-rock",
    1400,
    788,
    "Rooftops of an Abuja neighbourhood below Zuma Rock at sunset.",
    "Abuja",
  ),
  lagosApartments: photo(
    "lagos-apartments",
    1400,
    1050,
    "A modern apartment block still under construction, with a worker on the ground below.",
    "Lagos",
  ),
  abeokutaRooftops: photo(
    "abeokuta-rooftops",
    1400,
    934,
    "Red and brown roofs of houses spreading across green hills.",
    "Abeokuta",
  ),
  lagosAerial: photo(
    "lagos-aerial",
    1400,
    1050,
    "An aerial view of Lagos: new apartment blocks beside a busy road.",
    "Lagos",
  ),
  portHarcourtAerial: photo(
    "port-harcourt-aerial",
    1400,
    934,
    "An aerial view of Port Harcourt's riverbank homes and the road bridge.",
    "Port Harcourt",
  ),
  family: photo(
    "nigerian-family",
    900,
    1260,
    "A Nigerian family of four in bright traditional dress, smiling at the camera.",
  ),
  foundation: photo(
    "kaduna-foundation",
    900,
    1195,
    "A builder walking along a foundation trench with the first course of blocks laid.",
    "Kaduna",
  ),
  sandcrete: photo("sandcrete-blocks", 1400, 934, "Rows of freshly made sandcrete blocks drying in the sun."),
  blockwork: photo(
    "mortar-and-block-wall",
    1400,
    934,
    "A builder with a wheelbarrow of mortar in front of a half-built block wall.",
  ),
  formwork: photo(
    "formwork",
    900,
    1350,
    "Workers in red helmets on timber formwork and steel rods before concrete is poured.",
  ),
  roofing: photo(
    "scaffold-carry",
    900,
    1350,
    "Workers carrying loads on their heads up a scaffold of timber poles.",
  ),
} as const;

/** The hero carousel, in order, each with a short line about what the picture shows. */
export const HERO_SLIDES = [
  { photo: PHOTOS.abujaBungalow, line: "A home like this starts as a plot and a promise." },
  { photo: PHOTOS.enuguAerial, line: "Enugu, where many Nigerians abroad are building." },
  { photo: PHOTOS.abujaHouse, line: "Finished, because every stage was checked." },
  { photo: PHOTOS.lagosApartments, line: "Walls rising while you are thousands of miles away." },
  { photo: PHOTOS.abujaZumaRock, line: "Family houses across Abuja, built a milestone at a time." },
  { photo: PHOTOS.abeokutaRooftops, line: "Nigeria is full of homes someone built from far away." },
] as const;
