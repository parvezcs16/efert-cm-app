class LedgerEntry {
  final String id;
  final String sourceType;
  final String entryType;
  final String amount;
  final String reason;
  final String? guestSessionId;
  final String createdAt;

  LedgerEntry({
    required this.id,
    required this.sourceType,
    required this.entryType,
    required this.amount,
    required this.reason,
    required this.guestSessionId,
    required this.createdAt,
  });

  factory LedgerEntry.fromJson(Map<String, dynamic> json) => LedgerEntry(
    id: json['id'] as String,
    sourceType: json['source_type'] as String,
    entryType: json['entry_type'] as String,
    amount: json['amount'] as String,
    reason: json['reason'] as String,
    guestSessionId: json['guest_session_id'] as String?,
    createdAt: json['created_at'] as String,
  );
}

class Statement {
  final List<LedgerEntry> entries;
  final String totalDebit;
  final String totalCredit;
  final String netBalance;

  Statement({
    required this.entries,
    required this.totalDebit,
    required this.totalCredit,
    required this.netBalance,
  });

  factory Statement.fromJson(Map<String, dynamic> json) => Statement(
    entries: (json['entries'] as List)
        .map((e) => LedgerEntry.fromJson(e as Map<String, dynamic>))
        .toList(),
    totalDebit: json['total_debit'] as String,
    totalCredit: json['total_credit'] as String,
    netBalance: json['net_balance'] as String,
  );
}

const statementFrequencies = ['DAILY', 'WEEKLY', 'BIWEEKLY', 'MONTHLY'];
