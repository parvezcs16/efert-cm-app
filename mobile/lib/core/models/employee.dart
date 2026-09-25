/// Mirrors backend/app/models/enums.py and frontend/src/lib/types.ts.
/// Kept as plain strings (not Dart enums) so an unrecognized value from a
/// future backend change doesn't crash JSON parsing -- callers compare
/// against the string constants below instead of exhaustive enum matches.
class Employee {
  final String id;
  final String pNo;
  final String name;
  final String email;
  final String? department;
  final String status;
  final String role;
  final String passwordState;
  final String statementFrequency;
  final String? nextStatementDueAt;
  final String createdAt;

  Employee({
    required this.id,
    required this.pNo,
    required this.name,
    required this.email,
    required this.department,
    required this.status,
    required this.role,
    required this.passwordState,
    required this.statementFrequency,
    required this.nextStatementDueAt,
    required this.createdAt,
  });

  factory Employee.fromJson(Map<String, dynamic> json) => Employee(
    id: json['id'] as String,
    pNo: json['p_no'] as String,
    name: json['name'] as String,
    email: json['email'] as String,
    department: json['department'] as String?,
    status: json['status'] as String,
    role: json['role'] as String,
    passwordState: json['password_state'] as String,
    statementFrequency: json['statement_frequency'] as String,
    nextStatementDueAt: json['next_statement_due_at'] as String?,
    createdAt: json['created_at'] as String,
  );
}

const employeeRoles = [
  'EMPLOYEE',
  'SERVER',
  'KITCHEN_OPERATOR',
  'LOCATION_MANAGER',
  'SYSTEM_MANAGER',
  'FINANCE_ADMIN',
  'SYSTEM_ADMINISTRATOR',
];

const kitchenStaffRoles = [
  'SERVER',
  'KITCHEN_OPERATOR',
  'LOCATION_MANAGER',
  'SYSTEM_MANAGER',
  'SYSTEM_ADMINISTRATOR',
];

const adminRoles = [
  'LOCATION_MANAGER',
  'SYSTEM_MANAGER',
  'SYSTEM_ADMINISTRATOR',
  'FINANCE_ADMIN',
];
