from django.test import TestCase
from django.core.exceptions import (
    ValidationError,
    PermissionDenied
)

from papermerge.core.models import Document, Page
from papermerge.test.utils import create_root_user

from papermerge.test.parts.app_dr.models import Policy

class PartsTests(TestCase):

    def setUp(self):
        self.user = create_root_user()

    def test_basic(self):
        doc = Document.objects.create_document(
            file_name="test.pdf",
            title="Test #1",
            page_count=3,
            size="3",
            lang="DEU",
            user=self.user,
            parts={
                "extra_special_id": "DOC_XYZ_1"
            }
        )

        self.assertTrue(doc)
        self.assertEqual(
            doc.parts.extra_special_id,
            "DOC_XYZ_1"
        )

    def test_create_a_simple_document(self):
        policy = Policy.objects.create(name="Default Policy")

        doc = Document.objects.create_document(
            file_name="test.pdf",
            title="Test #1",
            page_count=3,
            size="3",
            lang="DEU",
            user=self.user,
            parts={
                'policy': policy
            }
        )

        self.assertEqual(
            doc.title,
            "Test #1"
        )
        self.assertEqual(
            doc.parts.policy.name,
            "Default Policy"
        )

    def test_assign_policy_after_document_creation(self):

        doc = Document.objects.create_document(
            file_name="test.pdf",
            size="3",
            lang="DEU",
            user=self.user,
            title="Test #1",
            page_count=3,
        )

        self.assertEqual(
            doc.title,
            "Test #1"
        )
        policy = Policy.objects.create(
            name="Default Policy"
        )
        self.assertFalse(
            doc.parts.policy
        )

        doc.parts.policy = policy
        doc.save()
        doc.refresh_from_db()

        dox = Document.objects.get(id=doc.id)

        self.assertEqual(
            dox.parts.policy.name,
            "Default Policy"
        )

    def test_permission_denied_on_restrictive_policy(self):
        """
        Document should not be allowed to be deleted if one
        document part restricts this operation.

        Data retention policy is a good example of this behaviour.
        Data retention app imposes a policy that will restrict document
        deletion.
        """
        doc = Document.objects.create_document(
            file_name="test.pdf",
            size="3",
            lang="DEU",
            user=self.user,
            title="Test #1",
            page_count=3,
        )

        policy = Policy.objects.create(
            name="Default Policy",
            allow_delete=False
        )

        doc.parts.policy = policy
        doc.save()

        dox = Document.objects.get(id=doc.id)

        with self.assertRaises(PermissionDenied):
            dox.delete()

    def test_create_document_with_101_pages(self):
        """
        test.parts.app_max_p contains a Document Part which
        invalidates any document with > 100 pages.

        Create a document with 101 pages and check that
        ValidationError is raised.
        """
        self.assertFalse(
            Document.objects.count()
        )

        self.assertFalse(
            Page.objects.count()
        )

        with self.assertRaises(ValidationError):
            Document.objects.create_document(
                title="Invoice BRT-0001",
                file_name="invoice.pdf",
                size="3",
                lang="DEU",
                user=self.user,
                # test.parts.app_0.models.Document allow MAX_PAGES=100
                page_count=101,
            )

        # No partially created docs were left.
        # If document creation failed - and its satellite models
        # - all transaction is rolled back
        self.assertFalse(
            Document.objects.count()
        )
        # No pages (from not yet created document) left.
        # If document creation failed - all transaction is rolled back
        self.assertFalse(
            Page.objects.count()
        )
