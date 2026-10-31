import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/queue_db.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'arrival_screen.dart';
import 'capture_target.dart';
import 'permissions_screen.dart';
import 'widgets.dart';

final spotChecksProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final list = await ref.read(servicesProvider).api.get<List<dynamic>>('/supervisors/me/spot-checks');
  return list.cast<Map<String, dynamic>>();
});

/// AND-SUPERVISOR-010: unannounced visits to make.
///
/// Spot checks are unannounced: the contractor is never told, and the client sees the result
/// only after operations close it. The project name and address are not shown here.
class SpotChecksScreen extends ConsumerWidget {
  const SpotChecksScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final checks = ref.watch(spotChecksProvider);
    return RefreshIndicator(
      onRefresh: () async => ref.refresh(spotChecksProvider.future),
      child: checks.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorRetry(e, () => ref.invalidate(spotChecksProvider)),
        data: (items) => items.isEmpty
            ? ListView(children: const [
                Padding(
                  padding: EdgeInsets.all(IbhSpace.s32),
                  child: Center(child: Text('No spot checks right now. Operations will message you when one is due.')),
                )
              ])
            : ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
                for (final s in items)
                  Card(
                    child: ListTile(
                      minVerticalPadding: IbhSpace.s12,
                      title: Text('Site visit · ${_when(s['scheduled_for'] as String)}'),
                      subtitle: Text(s['completed_at'] == null ? 'Unannounced: do not tell the contractor.' : 'Submitted'),
                      trailing: _chip(s),
                      onTap: () async {
                        await Navigator.of(context)
                            .push(MaterialPageRoute<void>(builder: (_) => SpotCheckScreen(spotCheck: s)));
                        ref.invalidate(spotChecksProvider);
                      },
                    ),
                  ),
              ]),
      ),
    );
  }

  static String _when(String iso) => DateTime.parse(iso).toLocal().toString().substring(0, 16);

  static Widget _chip(Map<String, dynamic> s) {
    if (s['completed_at'] != null) return const StatusChip('Submitted', tone: ChipTone.ok);
    final due = DateTime.parse(s['scheduled_for'] as String);
    return due.isBefore(DateTime.now().toUtc())
        ? const StatusChip('Due now', tone: ChipTone.warn)
        : const StatusChip('Scheduled', tone: ChipTone.neutral);
  }
}

class SpotCheckScreen extends ConsumerStatefulWidget {
  const SpotCheckScreen({super.key, required this.spotCheck});
  final Map<String, dynamic> spotCheck;

  @override
  ConsumerState<SpotCheckScreen> createState() => _SpotCheckScreenState();
}

class _SpotCheckScreenState extends ConsumerState<SpotCheckScreen> {
  final _findings = TextEditingController();
  List<QueuedCapture> _captures = const [];
  bool _busy = false;

  String get _ref => 'spot_check:${widget.spotCheck['id']}';
  bool get _done => widget.spotCheck['completed_at'] != null;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final all = await ref.read(servicesProvider).db.all(projectId: widget.spotCheck['project_id'] as String);
    if (mounted) setState(() => _captures = all.where((c) => c.contextRef == _ref && c.status != CaptureStatus.draft).toList());
  }

  Future<void> _capture() async {
    if (!await ensureCaptureReady(context, ref) || !mounted) return;
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => ArrivalScreen(
        target: CaptureTarget(
          projectId: widget.spotCheck['project_id'] as String,
          title: 'Spot check',
          contextRef: _ref,
          // The supervisor is not a member of the project, so the site boundary is not available
          // to the app; the server does the geofence check.
        ),
      ),
    ));
    await _load();
  }

  Future<void> _submit() async {
    setState(() => _busy = true);
    try {
      await ref.read(servicesProvider).api.post<Map<String, dynamic>>(
        '/spot-checks/${widget.spotCheck['id']}/complete',
        body: {'findings': _findings.text.trim()},
        idempotencyKey: 'spot-${widget.spotCheck['id']}',
      );
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Spot check')),
        body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          const Alert('Unannounced visit. Do not tell the contractor. The client sees the result only after '
              'operations close the check.', tone: ChipTone.info),
          const SizedBox(height: IbhSpace.s16),
          Text('Captures (${_captures.length})', style: IbhText.h3.copyWith(fontSize: 16)),
          const SizedBox(height: IbhSpace.s8),
          if (_captures.isEmpty) const Text('Take photos of what you see. Compare the work with the contractor\'s latest claim.'),
          Wrap(spacing: IbhSpace.s8, runSpacing: IbhSpace.s8, children: [
            for (final c in _captures)
              ClipRRect(
                borderRadius: BorderRadius.circular(IbhRadius.control),
                child: c.kind == 'video'
                    ? const SizedBox(width: 72, height: 72, child: ColoredBox(color: IbhColors.camera, child: Icon(Icons.videocam, color: IbhColors.white)))
                    : Image.file(File(c.filePath), width: 72, height: 72, fit: BoxFit.cover),
              ),
          ]),
          if (!_done) ...[
            const SizedBox(height: IbhSpace.s12),
            OutlinedButton.icon(onPressed: _capture, icon: const Icon(Icons.photo_camera_outlined), label: const Text('Capture')),
            const SizedBox(height: IbhSpace.s24),
            TextField(
              controller: _findings,
              maxLines: 5,
              decoration: const InputDecoration(labelText: 'What you found', helperText: 'At least 10 characters'),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: IbhSpace.s16),
            FilledButton(
              onPressed: _busy || _findings.text.trim().length < 10 || _captures.isEmpty ? null : _submit,
              child: const Text('Submit findings'),
            ),
          ] else
            Padding(
              padding: const EdgeInsets.only(top: IbhSpace.s16),
              child: Text('${widget.spotCheck['findings'] ?? ''}'),
            ),
        ]),
      );
}
