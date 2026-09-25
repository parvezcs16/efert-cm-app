class Guest {
  final String id;
  final String hostEmployeeId;
  final String name;
  final String companyName;
  final String cnic;
  final String guestType;
  final int accompanyingPersons;
  final String createdAt;

  Guest({
    required this.id,
    required this.hostEmployeeId,
    required this.name,
    required this.companyName,
    required this.cnic,
    required this.guestType,
    required this.accompanyingPersons,
    required this.createdAt,
  });

  factory Guest.fromJson(Map<String, dynamic> json) => Guest(
    id: json['id'] as String,
    hostEmployeeId: json['host_employee_id'] as String,
    name: json['name'] as String,
    companyName: json['company_name'] as String,
    cnic: json['cnic'] as String,
    guestType: json['guest_type'] as String,
    accompanyingPersons: json['accompanying_persons'] as int,
    createdAt: json['created_at'] as String,
  );
}

class GuestSession {
  final String id;
  final String guestId;
  final String hostEmployeeId;
  final String status;
  final String openedAt;
  final String? closedAt;
  final String tokenExpiresAt;

  GuestSession({
    required this.id,
    required this.guestId,
    required this.hostEmployeeId,
    required this.status,
    required this.openedAt,
    required this.closedAt,
    required this.tokenExpiresAt,
  });

  factory GuestSession.fromJson(Map<String, dynamic> json) => GuestSession(
    id: json['id'] as String,
    guestId: json['guest_id'] as String,
    hostEmployeeId: json['host_employee_id'] as String,
    status: json['status'] as String,
    openedAt: json['opened_at'] as String,
    closedAt: json['closed_at'] as String?,
    tokenExpiresAt: json['token_expires_at'] as String,
  );
}

class GuestSessionCreateResponse {
  final GuestSession session;
  final String qrToken;

  GuestSessionCreateResponse({required this.session, required this.qrToken});

  factory GuestSessionCreateResponse.fromJson(Map<String, dynamic> json) =>
      GuestSessionCreateResponse(
        session: GuestSession.fromJson(json['session'] as Map<String, dynamic>),
        qrToken: json['qr_token'] as String,
      );
}
