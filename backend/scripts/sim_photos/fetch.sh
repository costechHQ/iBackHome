#!/bin/sh
# Downloads real building-site photos from Pexels (free licence, no attribution needed) for
# `scripts/simulator.py --photos-dir scripts/sim_photos`. The JPEGs are not committed.
set -eu
cd "$(dirname "$0")"
for id in 11429199 4692281 26107204 3794760 10383588 10383579 10383583 7261621 9964624; do
  [ -s "$id.jpg" ] && continue
  curl -fsSL -A "Mozilla/5.0" -o "$id.jpg" \
    "https://images.pexels.com/photos/$id/pexels-photo-$id.jpeg?auto=compress&cs=tinysrgb&w=1280"
  echo "fetched $id.jpg"
done
