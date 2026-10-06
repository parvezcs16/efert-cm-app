import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/api_client.dart';
import '../auth_controller.dart';
import '../../../widgets/brand.dart';

enum _Step { credentials, otp, password }

/// Route `extra` for `/activate`. When [temporaryPassword] is given (a
/// first sign-in the server rejected with `activation_required`), the page
/// sends the activation code itself and opens on the code step.
class ActivationArgs {
  final String pNo;
  final String? temporaryPassword;

  const ActivationArgs(this.pNo, {this.temporaryPassword});
}

class ActivationPage extends StatefulWidget {
  final String? initialPNo;
  final String? temporaryPassword;

  const ActivationPage({super.key, this.initialPNo, this.temporaryPassword});

  @override
  State<ActivationPage> createState() => _ActivationPageState();
}

class _ActivationPageState extends State<ActivationPage> {
  _Step _step = _Step.credentials;
  late final TextEditingController _pNoController;
  late final TextEditingController _tempPasswordController;
  final _codeController = TextEditingController();
  final _newPasswordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  String? _changeToken;
  String? _error;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _pNoController = TextEditingController(text: widget.initialPNo ?? '');
    _tempPasswordController = TextEditingController(
      text: widget.temporaryPassword ?? '',
    );
    if (widget.temporaryPassword != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _start());
    }
  }

  @override
  void dispose() {
    _pNoController.dispose();
    _tempPasswordController.dispose();
    _codeController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _error = null;
      _loading = true;
    });
    try {
      await action();
    } on ApiException catch (err) {
      setState(() => _error = err.message);
    } catch (_) {
      setState(() => _error = 'Something went wrong');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _start() => _run(() async {
    await ApiClient.instance.post(
      '/auth/activation/start',
      body: {
        'p_no': _pNoController.text,
        'temporary_password': _tempPasswordController.text,
      },
    );
    if (!mounted) return;
    setState(() => _step = _Step.otp);
  });

  Future<void> _verifyOtp() => _run(() async {
    final data = await ApiClient.instance.post(
      '/auth/activation/verify-otp',
      body: {'p_no': _pNoController.text, 'code': _codeController.text},
    );
    _changeToken = (data as Map<String, dynamic>)['change_token'] as String;
    setState(() => _step = _Step.password);
  });

  Future<void> _setPassword() => _run(() async {
    if (_newPasswordController.text != _confirmPasswordController.text) {
      throw ApiException('Passwords do not match', 422);
    }
    final data = await ApiClient.instance.post(
      '/auth/activation/set-password',
      body: {
        'p_no': _pNoController.text,
        'change_token': _changeToken,
        'new_password': _newPasswordController.text,
      },
    );
    final map = data as Map<String, dynamic>;
    await ApiClient.instance.authStorage.setTokens(
      map['access_token'] as String,
      map['refresh_token'] as String,
    );
    if (!mounted) return;
    await context.read<AuthController>().refreshProfile();
    if (!mounted) return;
    context.go('/');
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
                  const Center(child: BrandLogo(height: 64)),
                  const SizedBox(height: 32),
                  Text(
                    'Activate your account',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 4),
                  Text(switch (_step) {
                    _Step.credentials =>
                      'Enter your P-Number and temporary password.',
                    _Step.otp =>
                      'This is your first sign-in. Enter the code sent to '
                          'your email to activate your account.',
                    _Step.password => 'Choose a new password.',
                  }),
                  const SizedBox(height: 24),
                  if (_step == _Step.credentials) ...[
                    TextField(
                      controller: _pNoController,
                      decoration: const InputDecoration(labelText: 'P-Number'),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _tempPasswordController,
                      decoration: const InputDecoration(
                        labelText: 'Temporary password',
                      ),
                      obscureText: true,
                    ),
                  ] else if (_step == _Step.otp) ...[
                    TextField(
                      controller: _codeController,
                      decoration: const InputDecoration(
                        labelText: '6-digit code',
                      ),
                      keyboardType: TextInputType.number,
                      maxLength: 6,
                    ),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: _loading ? null : _start,
                        child: const Text('Resend code'),
                      ),
                    ),
                  ] else ...[
                    TextField(
                      controller: _newPasswordController,
                      decoration: const InputDecoration(
                        labelText: 'New password',
                      ),
                      obscureText: true,
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _confirmPasswordController,
                      decoration: const InputDecoration(
                        labelText: 'Confirm password',
                      ),
                      obscureText: true,
                    ),
                  ],
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
                  FilledButton(
                    onPressed: _loading
                        ? null
                        : switch (_step) {
                            _Step.credentials => _start,
                            _Step.otp => _verifyOtp,
                            _Step.password => _setPassword,
                          },
                    child: _loading
                        ? const SizedBox(
                            height: 18,
                            width: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Text(switch (_step) {
                            _Step.credentials => 'Send activation code',
                            _Step.otp => 'Verify code',
                            _Step.password => 'Activate and sign in',
                          }),
                  ),
                  const SizedBox(height: 12),
                  TextButton(
                    onPressed: () => context.go('/login'),
                    child: const Text('Back to sign in'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
