import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/server_config.dart';

/// Login-screen link showing the current server, opening [_ServerDialog].
/// Hidden entirely when built with `--dart-define=ALLOW_SERVER_OVERRIDE=false`.
class ServerSettingsButton extends StatefulWidget {
  const ServerSettingsButton({super.key});

  @override
  State<ServerSettingsButton> createState() => _ServerSettingsButtonState();
}

class _ServerSettingsButtonState extends State<ServerSettingsButton> {
  Future<void> _open() async {
    final changed = await showDialog<bool>(
      context: context,
      builder: (_) => const _ServerDialog(),
    );
    if (changed == true && mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    if (!ServerConfig.allowOverride) return const SizedBox.shrink();
    return TextButton.icon(
      onPressed: _open,
      icon: const Icon(Icons.dns_outlined, size: 18),
      label: Text('Server: ${Uri.parse(ApiClient.baseUrl).authority}'),
    );
  }
}

class _ServerDialog extends StatefulWidget {
  const _ServerDialog();

  @override
  State<_ServerDialog> createState() => _ServerDialogState();
}

class _ServerDialogState extends State<_ServerDialog> {
  late final TextEditingController _controller = TextEditingController(
    text: Uri.parse(ApiClient.baseUrl).authority,
  );
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _apply(String? value) async {
    setState(() {
      _error = null;
      _busy = true;
    });
    try {
      await ServerConfig.setOverride(value);
      await ApiClient.instance.get('/health');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Connected to ${ApiClient.baseUrl}')),
      );
      Navigator.of(context).pop(true);
    } on FormatException catch (err) {
      setState(() => _error = err.message);
    } on ApiException catch (err) {
      // Keep the saved address (the server may just not be started yet),
      // but tell the user it isn't reachable right now.
      setState(() => _error = 'Saved, but: ${err.message}');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Server address'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            "Your PC's IP and port, e.g. 172.23.48.119:8000 "
            '(or :8080 when running with Docker).',
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _controller,
            decoration: const InputDecoration(labelText: 'IP:port or URL'),
            keyboardType: TextInputType.url,
            autocorrect: false,
            onSubmitted: _busy ? null : (v) => _apply(v),
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
        ],
      ),
      actions: [
        if (ServerConfig.override != null)
          TextButton(
            onPressed: _busy ? null : () => _apply(null),
            child: const Text('Reset'),
          ),
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(true),
          child: const Text('Close'),
        ),
        FilledButton(
          onPressed: _busy ? null : () => _apply(_controller.text),
          child: _busy
              ? const SizedBox(
                  height: 18,
                  width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Save & test'),
        ),
      ],
    );
  }
}
