import datetime
import unittest

from emmet.utils.payments import PaymentError
from emmet.utils.payments import build_virtual_barcode
from emmet.utils.payments import calculate_finnish_reference
from emmet.utils.payments import generate_member_reference
from emmet.utils.payments import generate_rf_reference
from emmet.utils.payments import normalize_iban
from emmet.utils.payments import parse_amount
from emmet.utils.payments import parse_due_date


class PaymentUtilityTests(unittest.TestCase):
    def test_finnish_reference_official_example(self) -> None:
        self.assertEqual(calculate_finnish_reference("123456"), "1234561")

    def test_member_reference_is_deterministic(self) -> None:
        self.assertEqual(generate_member_reference(2026, 12), "2026121")

    def test_rf_reference_generation(self) -> None:
        self.assertEqual(generate_rf_reference("1234561"), "RF341234561")

    def test_version_4_barcode_length(self) -> None:
        barcode = build_virtual_barcode(
            iban="FI2112345600000785",
            euros=10,
            cents=0,
            due_date=datetime.date(2026, 12, 31),
            reference="1234561",
            version=4,
        )

        self.assertEqual(len(barcode), 54)
        self.assertEqual(
            barcode, "421123456000007850000100000000000000000001234561261231"
        )

    def test_version_5_barcode_length(self) -> None:
        barcode = build_virtual_barcode(
            iban="FI2112345600000785",
            euros=10,
            cents=0,
            due_date=datetime.date(2026, 12, 31),
            reference="1234561",
            version=5,
        )

        self.assertEqual(len(barcode), 54)
        self.assertEqual(
            barcode, "521123456000007850000100034000000000000001234561261231"
        )

    def test_non_fi_iban_is_valid_but_not_barcode_encodable(self) -> None:
        self.assertEqual(
            normalize_iban("IE29SUMU99036512304457"), "IE29SUMU99036512304457"
        )

        with self.assertRaisesRegex(PaymentError, "exactly 16 digits"):
            build_virtual_barcode(
                iban="IE29SUMU99036512304457",
                euros=10,
                cents=0,
                due_date=datetime.date(2026, 12, 31),
                reference="1234561",
                version=5,
            )

    def test_invalid_inputs_are_rejected(self) -> None:
        with self.assertRaises(PaymentError):
            parse_amount("-1")
        with self.assertRaises(PaymentError):
            parse_amount("1000000")
        with self.assertRaises(PaymentError):
            parse_due_date("31.12.2026")
        with self.assertRaises(PaymentError):
            normalize_iban("FI2112345600000786")


if __name__ == "__main__":
    unittest.main()
