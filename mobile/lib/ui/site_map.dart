import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/ibh_tokens.dart';

/// The arrival-check map: the site boundary (navy outline, light fill), the 25 m tolerance band
/// (dashed) and where the phone is (blue dot with its GPS accuracy). Drawn with flat shapes, no map
/// tiles, so it works offline and is light on low-end phones. The words beside it say inside or
/// outside; the picture is never the only way to read the result.
class SiteMap extends StatelessWidget {
  const SiteMap({super.key, required this.ring, this.lat, this.lon, this.accuracyM, this.toleranceM = 25, this.height = 240});

  /// GeoJSON ring: `[lon, lat]` pairs.
  final List<List<double>>? ring;
  final double? lat;
  final double? lon;
  final double? accuracyM;
  final double toleranceM;
  final double height;

  @override
  Widget build(BuildContext context) => Semantics(
        label: ring == null ? 'No site boundary yet' : 'Map of the site boundary and your position',
        child: ClipRRect(
          borderRadius: BorderRadius.circular(IbhRadius.card),
          child: Container(
            height: height,
            width: double.infinity,
            color: IbhColors.mapLand,
            child: ring == null
                ? const Center(child: Text('No site boundary yet', style: TextStyle(color: IbhColors.muted)))
                : CustomPaint(painter: _MapPainter(ring!, lat, lon, accuracyM, toleranceM)),
          ),
        ),
      );
}

class _MapPainter extends CustomPainter {
  _MapPainter(this.ring, this.lat, this.lon, this.accuracy, this.tolerance);

  final List<List<double>> ring;
  final double? lat;
  final double? lon;
  final double? accuracy;
  final double tolerance;

  @override
  void paint(Canvas canvas, Size size) {
    final lat0 = ring.map((p) => p[1]).reduce((a, b) => a + b) / ring.length;
    final lon0 = ring.map((p) => p[0]).reduce((a, b) => a + b) / ring.length;
    final k = math.cos(lat0 * math.pi / 180);
    const m = 111320.0;
    // Metres east / north of the site centre.
    Offset toM(double lo, double la) => Offset((lo - lon0) * k * m, -(la - lat0) * m);

    final site = [for (final p in ring) toM(p[0], p[1])];
    final centre = site.fold(Offset.zero, (a, b) => a + b) / site.length.toDouble();
    // The tolerance band: every corner pushed out from the centre by the allowance (a plot is small, so
    // this is a close enough picture of a 25 m buffer).
    final band = [
      for (final p in site)
        () {
          final v = p - centre;
          final d = v.distance == 0 ? 1.0 : v.distance;
          return p + v / d * tolerance;
        }()
    ];
    final me = lat == null || lon == null ? null : toM(lon!, lat!);

    final pts = [...band, ?me];
    final minX = pts.map((p) => p.dx).reduce(math.min), maxX = pts.map((p) => p.dx).reduce(math.max);
    final minY = pts.map((p) => p.dy).reduce(math.min), maxY = pts.map((p) => p.dy).reduce(math.max);
    const pad = 28.0;
    final w = math.max(maxX - minX, 1.0), h = math.max(maxY - minY, 1.0);
    final scale = math.min((size.width - pad * 2) / w, (size.height - pad * 2) / h);
    final dx = (size.width - w * scale) / 2 - minX * scale;
    final dy = (size.height - h * scale) / 2 - minY * scale;
    Offset px(Offset o) => Offset(o.dx * scale + dx, o.dy * scale + dy);

    Path poly(List<Offset> o) {
      final path = Path()..moveTo(px(o.first).dx, px(o.first).dy);
      for (final p in o.skip(1)) {
        path.lineTo(px(p).dx, px(p).dy);
      }
      return path..close();
    }

    // Streets: two light bands, for orientation only.
    final street = Paint()..color = IbhColors.white;
    canvas.drawRect(Rect.fromLTWH(size.width * 0.12, 0, 14, size.height), street);
    canvas.drawRect(Rect.fromLTWH(0, size.height * 0.88, size.width, 14), street);

    canvas.drawPath(poly(site), Paint()..color = IbhColors.navy900.withValues(alpha: 0.08));
    canvas.drawPath(poly(site), Paint()..style = PaintingStyle.stroke..strokeWidth = 2..color = IbhColors.navy900..strokeJoin = StrokeJoin.round);

    final dash = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.5..color = IbhColors.lineStrong;
    for (final metric in poly(band).computeMetrics()) {
      var d = 0.0;
      while (d < metric.length) {
        canvas.drawPath(metric.extractPath(d, math.min(d + 6, metric.length)), dash);
        d += 11;
      }
    }

    if (me != null) {
      final c = px(me);
      final halo = ((accuracy ?? 10) * scale).clamp(10.0, 60.0);
      canvas.drawCircle(c, halo, Paint()..color = IbhColors.accent.withValues(alpha: 0.18));
      canvas.drawCircle(c, 7, Paint()..color = IbhColors.white);
      canvas.drawCircle(c, 5.5, Paint()..color = IbhColors.accent);
    }
  }

  @override
  bool shouldRepaint(_MapPainter old) => old.lat != lat || old.lon != lon || old.accuracy != accuracy || old.ring != ring;
}
