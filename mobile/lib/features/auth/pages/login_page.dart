import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/api_client.dart';
import '../auth_controller.dart';
import 'activation_page.dart';
import '../../../widgets/brand.dart';
import '../../../widgets/server_settings.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _pNoController = TextEditingController();
  final _passwordController = TextEditingController();
  String? _error;
  bool _loading = false;

  Future<void> _submit() async {
    setState(() {
      _error = null;
      _loading = true;
    });
    try {
      final auth = context.read<AuthController>();
      final mustChangePassword = await auth.login(
        _pNoController.text,
        _passwordController.text,
      );
      if (!mounted) return;
      if (mustChangePassword) {
        context.go('/activate', extra: ActivationArgs(_pNoController.text));
      } else {
        context.go('/');
      }
    } on ApiException catch (err) {
      if (err.errorCode == 'activation_required') {
        // First sign-in with the temporary password: the server has already
        // verified it, so continue straight into activation instead of
        // making the user re-enter it on a separate screen.
        context.go(
          '/activate',
          extra: ActivationArgs(
            _pNoController.text,
            temporaryPassword: _passwordController.text,
          ),
        );
        return;
      }
      setState(() => _error = err.message);
    } catch (_) {
      setState(() => _error = 'Something went wrong');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

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
                    'Sign in',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 4),
                  const Text('Use your P-Number and password.'),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _pNoController,
                    decoration: const InputDecoration(labelText: 'P-Number'),
                    textInputAction: TextInputAction.next,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _passwordController,
                    decoration: const InputDecoration(labelText: 'Password'),
                    obscureText: true,
                    onSubmitted: (_) => _submit(),
                  ),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () => context.go('/forgot-password'),
                      child: const Text('Forgot password?'),
                    ),
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
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: _loading ? null : _submit,
                    child: _loading
                        ? const SizedBox(
                            height: 18,
                            width: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Sign in'),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text('New here?'),
                      TextButton(
                        onPressed: () => context.go('/register'),
                        child: const Text('Register'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  const ServerSettingsButton(),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
