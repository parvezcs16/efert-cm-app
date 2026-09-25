import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_client.dart';

enum _Step { request, otp, password, done }

class ForgotPasswordPage extends StatefulWidget {
  const ForgotPasswordPage({super.key});

  @override
  State<ForgotPasswordPage> createState() => _ForgotPasswordPageState();
}

class _ForgotPasswordPageState extends State<ForgotPasswordPage> {
  _Step _step = _Step.request;
  final _pNoController = TextEditingController();
  final _codeController = TextEditingController();
  final _newPasswordController = TextEditingController();
  String? _changeToken;
  String? _error;
  bool _loading = false;

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _error = null;
      _loading = true;
    });
    try {
      await action();
    } on ApiException catch (err) {
      setState(() => _error = err.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _request() => _run(() async {
    await ApiClient.instance.post(
      '/auth/password/forgot',
      body: {'p_no': _pNoController.text},
    );
    setState(() => _step = _Step.otp);
  });

  Future<void> _verify() => _run(() async {
    final data = await ApiClient.instance.post(
      '/auth/password/reset/verify-otp',
      body: {'p_no': _pNoController.text, 'code': _codeController.text},
    );
    _changeToken = (data as Map<String, dynamic>)['change_token'] as String;
    setState(() => _step = _Step.password);
  });

  Future<void> _reset() => _run(() async {
    await ApiClient.instance.post(
      '/auth/password/reset',
      body: {
        'p_no': _pNoController.text,
        'change_token': _changeToken,
        'new_password': _newPasswordController.text,
      },
    );
    setState(() => _step = _Step.done);
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Reset your password',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 4),
                  Text(switch (_step) {
                    _Step.request =>
                      'Enter your P-Number to receive a reset code.',
                    _Step.otp => 'Enter the code sent to your email.',
                    _Step.password => 'Choose a new password.',
                    _Step.done => 'Your password has been reset.',
                  }),
                  const SizedBox(height: 24),
                  if (_step == _Step.request)
                    TextField(
                      controller: _pNoController,
                      decoration: const InputDecoration(labelText: 'P-Number'),
                    )
                  else if (_step == _Step.otp)
                    TextField(
                      controller: _codeController,
                      decoration: const InputDecoration(
                        labelText: '6-digit code',
                      ),
                      keyboardType: TextInputType.number,
                      maxLength: 6,
                    )
                  else if (_step == _Step.password)
                    TextField(
                      controller: _newPasswordController,
                      decoration: const InputDecoration(
                        labelText: 'New password',
                      ),
                      obscureText: true,
                    ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      _error!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  if (_step != _Step.done)
                    FilledButton(
                      onPressed: _loading
                          ? null
                          : switch (_step) {
                              _Step.request => _request,
                              _Step.otp => _verify,
                              _Step.password => _reset,
                              _Step.done => null,
                            },
                      child: _loading
                          ? const SizedBox(
                              height: 18,
                              width: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : Text(switch (_step) {
                              _Step.request => 'Send reset code',
                              _Step.otp => 'Verify code',
                              _Step.password => 'Reset password',
                              _Step.done => '',
                            }),
                    )
                  else
                    FilledButton(
                      onPressed: () => context.go('/login'),
                      child: const Text('Back to sign in'),
                    ),
                  if (_step != _Step.done) ...[
                    const SizedBox(height: 12),
                    TextButton(
                      onPressed: () => context.go('/login'),
                      child: const Text('Back to sign in'),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
