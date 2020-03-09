from django.http import Http404

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import (JSONParser, FileUploadParser)
from rest_framework.permissions import IsAuthenticated

from papermerge.core.models import Document
from papermerge.core.serializers import DocumentSerializer


class PagesClipboard:
    """
    Stores in current session information about cuted pages and their
    documents.
    Pages information is stored into the session in following
    format:

        {
            doc_id_1: [page_num_1a, page_num_2a, ...],
            doc_id_2: [page_num_1b, page_num_2b, ...],
            doc_id_3: [page_num_1c, page_num_2c, ...]
        }
    Which means user cutted page_num_1a, page_num_2a from doc_id_1,
    page_num_1b, page_num_2b from doc_id_2 etc
    """

    def __init__(self, request):
        self.request = request

    def put(self, doc_id, page_nums):
        user = self.request.user.id
        clipboard_id = f"{user}.clipboard.pages"

        if not self.request.session[clipboard_id]:
            self.request.session[clipboard_id] = {}
            self.request.session[clipboard_id][doc_id] = page_nums
        else:
            self.request.session[clipboard_id][doc_id] = page_nums

        self.request.session.modified = True

    def get(self):
        user = self.request.user.id
        clipboard_id = f"{user}.clipboard.pages"

        return self.request.session[clipboard_id]

    def reset(self, doc_id=None):
        pass


class PagesView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, doc_id):
        """
        Deletes Pages from doc_id document
        """
        try:
            doc = Document.objects.get(id=doc_id)
        except Document.DoesNotExist:
            raise Http404("Document does not exists")

        page_nums = request.GET.getlist('pages[]')
        page_nums = [int(number) for number in page_nums]

        doc.delete_pages(page_numbers=page_nums)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request, doc_id):
        """
        Reorders pages from doc_id document
        """
        try:
            doc = Document.objects.get(id=doc_id)
        except Document.DoesNotExist:
            raise Http404("Document does not exists")

        doc.reorder_pages(request.data)

        return Response(status=status.HTTP_204_NO_CONTENT)


class PagesCutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, doc_id):
        """
        Cut Pages from doc_id document.
        It adds pages to clipboard designated for pages
        which where cut.
        """
        try:
            Document.objects.get(id=doc_id)
        except Document.DoesNotExist:
            raise Http404("Document does not exists")

        page_nums = request.POST.getlist('pages[]')
        page_nums = [int(number) for number in page_nums]

        clipboard = PagesClipboard(request)
        clipboard.put(doc_id=doc_id, page_nums=page_nums)

        return Response(status=status.HTTP_204_NO_CONTENT)


class PagesPasteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Paste pages.
        Pages can be pasted into a document or into a Folder.
        When pasted into a folder - a new document containing those
        pages is created. When pasted into a document - those pages will
        added to the respective document.

        """
        node_id = request.POST.get('node_id', False)
        pivot_type = request.POST.get('pivot_type', 'before')
        pivot_page_num = request.POST.get('pivot_page_num', '1')
        node = BaseTreeNode.objects.filter(id=node_id).first()

        clipboard = PagesClipboard(request)
        clipboard.get()

        # if node is Folder:
        #   Document.create_new_merged_document(
        #       clipboard.get(), parent_id=node_id
        #   )
        # else:
        #   pivot_type = before | after
        #   node.paste(
        #       clipboard.get(),
        #       pivot={type: pivot_type, page_num: pivot_page_num}
        #   )

        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        documents = Document.objects.all()
        serializer = DocumentSerializer(documents, many=True)

        return Response(serializer.data)


class DocumentUploadView(APIView):
    """
    REST API for uploading a file.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [FileUploadParser]

    def put(self, request, filename):
        file_obj = request.data['file']

        Document.import_file(
            file_obj.temporary_file_path(),
            username=request.user.username,
            file_title=filename
        )

        return Response(status=204)


class DocumentView(APIView):

    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            raise Http404

    def get(self, request, pk):
        """
        Retrieve, update or delete a document.
        """
        document = self.get_object(pk)

        serializer = DocumentSerializer(document)

        return Response(serializer.data)

    def put(self, request, pk):
        data = JSONParser().parse(request)
        document = self.get_object(pk)

        serializer = DocumentSerializer(document, data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):

        document = self.get_object(pk)
        document.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
