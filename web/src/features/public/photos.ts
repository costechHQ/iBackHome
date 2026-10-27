// Landing-page photography: free-licence stock from Pexels, resized by hand into public/landing/. These are
// illustrations of Nigerian homes and building sites, not iBackHome customers' projects, and the pages say so.

export type Photo = { src: string; width: number; height: number; alt: string };

const photo = (name: string, width: number, height: number, alt: string): Photo => ({
  src: `/landing/${name}.jpg`,
  width,
  height,
  alt,
});

export const PHOTOS = {
  abujaBungalow: photo(
    "abuja-bungalow",
    1400,
    935,
    "A blue and white bungalow with arched doorways, palm trees and a trimmed hedge.",
  ),
  abujaHouse: photo(
    "abuja-house",
    900,
    1350,
    "A finished three-storey house with a brick feature wall, balconies and a boundary fence.",
  ),
  enuguAerial: photo(
    "enugu-aerial",
    1400,
    754,
    "An aerial view of Enugu: red roofs among trees and a lake at dusk.",
  ),
  abujaZumaRock: photo(
    "abuja-zuma-rock",
    1400,
    788,
    "Rooftops of an Abuja neighbourhood below Zuma Rock at sunset.",
  ),
  lagosApartments: photo(
    "lagos-apartments",
    1400,
    1050,
    "A modern apartment block still under construction, with a worker on the ground below.",
  ),
  duplexWhite: photo(
    "modern-duplex-white",
    808,
    632,
    "A modern white duplex with a cantilevered upper floor, stone cladding, a green terrace and cars in the carport.",
  ),
  duplexDusk: photo(
    "modern-duplex-dusk",
    1400,
    1400,
    "A modern white and timber duplex at dusk with glowing windows, roof gardens and palm trees.",
  ),
  sandShovelling: photo(
    "sand-shovelling-enugu",
    640,
    960,
    "A woman in a bright headwrap and wax-print wrapper shovelling red building sand at a site in Enugu.",
  ),
  hammeringFormwork: photo(
    "hammering-formwork",
    640,
    1140,
    "A Black carpenter in a yellow hard hat and hi-vis vest hammering a nail into timber formwork.",
  ),
  wheelbarrowEarth: photo(
    "wheelbarrow-earth",
    640,
    427,
    "A worker shovelling red earth into a wheelbarrow in front of a sandcrete block wall.",
  ),
  siteCrewScaffold: photo(
    "site-crew-scaffold",
    640,
    960,
    "A crew of workers in hi-vis vests and hard hats at the foot of a scaffold and ladder on a building site.",
  ),
  rebarCrew: photo(
    "rebar-crew",
    640,
    398,
    "Two site workers in yellow hard hats tying steel reinforcement, with more workers and rebar behind them.",
  ),
  smilingCrew: photo(
    "smiling-crew",
    640,
    427,
    "A smiling crew of five young builders in hi-vis vests, covered in dust from the site.",
  ),
  engineerPhone: photo(
    "engineer-phone",
    900,
    1350,
    "A civil engineer in a white hard hat and white shirt checking her phone on a block wall, with site plans on the ground beside her.",
  ),
  engineerPlans: photo(
    "engineer-plans",
    800,
    1200,
    "A woman engineer in a white hard hat studying a site plan in tall dry grass.",
  ),
  youngEngineer: photo(
    "young-engineer",
    800,
    1063,
    "A smiling young Black engineer in a blue hard hat standing with his hands in his pockets.",
  ),
  siteLeadRoad: photo(
    "site-lead-road",
    1100,
    786,
    "A site lead in a hi-vis vest holding a yellow hard hat on a newly built road.",
  ),
  abujaModernHome: photo(
    "abuja-modern-home",
    900,
    1350,
    "A modern three-storey family home in Abuja with a brown tiled roof, brick feature panels and a boundary wall.",
  ),
  villaPool: photo(
    "villa-pool",
    1000,
    750,
    "A contemporary two-storey home with a paved courtyard and a swimming pool under a bright sky.",
  ),
  nairaNotesWide: photo(
    "naira-notes-wide",
    1600,
    1067,
    "Two hundred and five hundred naira notes fanned out on a dark background.",
  ),
  nairaPayout: photo(
    "naira-payout",
    700,
    1049,
    "A young Nigerian man in a plum shirt looking down at naira notes in his hands.",
  ),
  buildingGoldenHour: photo(
    "building-golden-hour",
    1600,
    1067,
    "A concrete building under construction in warm evening light, its upper floor still in timber formwork.",
  ),
  engineerTape: photo(
    "engineer-tape",
    900,
    1350,
    "A woman engineer in a white hard hat and white shirt measuring on an open site, site plans spread on the ground at her feet.",
  ),
  womenEngineers: photo(
    "women-engineers",
    900,
    675,
    "Two Black women engineers in yellow hard hats and safety glasses looking at something together on site.",
  ),
  villaPoolPalms: photo(
    "villa-pool-palms",
    1600,
    1067,
    "A modern white villa with glass balconies, palm trees and a long swimming pool in the sunshine.",
  ),
  cementStack: photo(
    "cement-stack",
    800,
    1067,
    "A neat stack of cement bags on a pallet against a white wall.",
  ),
  siteSupervisors: photo(
    "site-supervisors",
    1200,
    800,
    "Two site supervisors in hard hats and hi-vis vests checking a tablet together in front of a row of new houses.",
  ),
  lawLibrary: photo(
    "law-library",
    1200,
    800,
    "A Black woman in dark formal robes reading a document while taking a call, in front of shelves of law books.",
  ),
  headsetSmile: photo(
    "headset-smile",
    700,
    1050,
    "A smiling customer-support agent in a mint blazer and headset, sitting at a laptop.",
  ),
  officeDocuments: photo(
    "office-documents",
    1800,
    1200,
    "A Black businesswoman in a striped blouse going through papers at an office desk, a laptop and a coffee beside her.",
  ),
  supportTeam: photo(
    "support-team",
    1800,
    1200,
    "A young Black woman with purple braids and glasses working at a desk in a bright office, colleagues on headsets behind her.",
  ),
  lagosAerial: photo(
    "lagos-aerial",
    1400,
    1050,
    "An aerial view of Lagos: new apartment blocks beside a busy road.",
  ),
  portHarcourtAerial: photo(
    "port-harcourt-aerial",
    1400,
    934,
    "An aerial view of Port Harcourt's riverbank homes and the road bridge.",
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

/** The hero carousel, in order: a short line about each picture and where to anchor it when the frame crops it. */
export const HERO_SLIDES = [
  {
    photo: PHOTOS.duplexWhite,
    line: "A home like this starts as a plot and a promise.",
    position: "object-center",
  },
  {
    photo: PHOTOS.duplexDusk,
    line: "Come home to the house you approved, stage by stage.",
    position: "object-bottom",
  },
  {
    photo: PHOTOS.abujaBungalow,
    line: "Family houses, built a milestone at a time.",
    position: "object-center",
  },
  {
    photo: PHOTOS.abujaHouse,
    line: "Finished, because every stage was checked.",
    position: "object-center",
  },
  {
    photo: PHOTOS.lagosApartments,
    line: "Walls rising while you are thousands of miles away.",
    position: "object-center",
  },
] as const;
