// SAMPLE DATA, NOT REAL. Everything in this file stands in for backend routes that do not exist yet:
//
//  - MX-05  material orders: `GET /projects/{id}/orders` (list and read). Only `POST` exists today.
//  - MX-11  the in-app alerts feed: `GET /notifications`.
//
// The screens read it only when `Config.mocks` is on (debug builds), and label what they show as
// sample data. When the routes exist, replace the three functions below with calls to the API and
// delete this file. The shapes follow `Docs/design/.../fixtures.json` (`mock_adapters`).
//
// Money is whole kobo. The names and amounts are invented.

import 'config.dart';

const _sampleOrders = <Map<String, Object?>>[
  {
    '_mock': true,
    'id': 'sample-order-1',
    'display_ref': 'O-0152',
    'title': 'Rework materials',
    'supplier': 'Sample Supplier',
    'milestone': 'Plastering',
    'status': 'requested',
    'total_minor': 34950000,
    'currency': 'NGN',
    'created_at': '2027-01-07T10:00:00Z',
    'items': [
      {'item': 'Fibre mesh, 50 m roll', 'unit': 'roll', 'quantity': '6', 'unit_price_minor': 1500000},
      {'item': 'Fine plastering sand', 'unit': 'tonne', 'quantity': '10', 'unit_price_minor': 2595000},
    ],
  },
  {
    '_mock': true,
    'id': 'sample-order-2',
    'display_ref': 'O-0141',
    'title': 'Plastering materials',
    'supplier': 'Sample Building Materials',
    'milestone': 'Plastering',
    'status': 'approved',
    'total_minor': 217200000,
    'currency': 'NGN',
    'created_at': '2026-12-15T14:22:00Z',
    'items': [
      {'item': 'Cement, 50 kg bag', 'unit': 'bag', 'quantity': '140', 'unit_price_minor': 1030000},
      {'item': 'Sharp sand', 'unit': 'tonne', 'quantity': '20', 'unit_price_minor': 2150000},
      {'item': 'Fine plastering sand', 'unit': 'tonne', 'quantity': '10', 'unit_price_minor': 2595000},
      {'item': 'Fibre mesh, 50 m roll', 'unit': 'roll', 'quantity': '6', 'unit_price_minor': 1500000},
    ],
  },
  {
    '_mock': true,
    'id': 'sample-order-3',
    'display_ref': 'O-0127',
    'title': '9-inch blocks, 6,000',
    'supplier': 'Sample Block Works',
    'milestone': 'Blockwork',
    'status': 'paid',
    'total_minor': 312000000,
    'currency': 'NGN',
    'created_at': '2026-11-12T09:00:00Z',
    'items': [
      {'item': '9-inch block', 'unit': 'piece', 'quantity': '6000', 'unit_price_minor': 52000},
    ],
  },
];

const _sampleAlerts = <Map<String, Object?>>[
  {
    '_mock': true,
    'title': 'A milestone was sent back for rework',
    'body': 'The supervisor says some items were not ready. Tap to see why.',
    'sent_at': '2027-01-06T14:41:00Z',
    'unread': true,
  },
  {
    '_mock': true,
    'title': 'Supervisor visit booked',
    'body': 'The supervisor visits on the date you were told.',
    'sent_at': '2027-01-04T09:16:00Z',
    'unread': false,
  },
  {
    '_mock': true,
    'title': 'A milestone is funded',
    'body': 'You can start work.',
    'sent_at': '2026-12-14T10:09:00Z',
    'unread': false,
  },
];

/// Material orders for a project (MX-05). Empty unless mocks are on.
Future<List<Map<String, Object?>>> sampleOrders() async => Config.mocks ? _sampleOrders : const [];

/// A single order by id (MX-05). Null unless mocks are on.
Future<Map<String, Object?>?> sampleOrder(String id) async {
  if (!Config.mocks) return null;
  for (final o in _sampleOrders) {
    if (o['id'] == id) return o;
  }
  return null;
}

/// The signed-in user's alerts, newest first (MX-11). Empty unless mocks are on.
Future<List<Map<String, Object?>>> sampleAlerts() async => Config.mocks ? _sampleAlerts : const [];
