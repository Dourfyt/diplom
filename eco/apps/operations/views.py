"""
CRUD для журнала движений отходов (Movement).

Список поддерживает фильтр по организации (GET-параметр organization).
Экспорт в PDF и XML — см. MovementExportPdfView, MovementExportXmlView.
"""

from io import BytesIO
import xml.etree.ElementTree as ET

from urllib.parse import urlencode

from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.integrations.exceptions import ApiError
from apps.integrations.mixins import (
    EcologistOrManagerRequiredMixin,
    EcologistRequiredMixin,
    RemoteApiReadOnlyMixin,
)
from apps.integrations.remote_data import get_remote_service, movements_for_request
from apps.operations.forms import MovementForm
from apps.operations.models import Movement
from apps.operations.pdf_fonts import ensure_pdf_cyrillic_fonts


def movements_queryset_for_request(request):
    """Операции с сервера API (общая БД проекта)."""
    return movements_for_request(request)


def movement_list_querystring(request) -> str:
    """Параметры GET без page — пагинация и экспорт (PDF, XML)."""
    params = {}
    org = request.GET.get("organization")
    if org not in (None, ""):
        params["organization"] = org
    for key in ("date_from", "date_to"):
        value = request.GET.get(key, "").strip()
        if value:
            params[key] = value
    q = request.GET.get("q", "").strip()
    if q:
        params["q"] = q
    return urlencode(params)


class MovementListView(EcologistOrManagerRequiredMixin, ListView):
    """Список операций: пагинация, фильтр по организации, поиск по названию организации и отхода."""

    model = Movement
    template_name = "operations/movement_list.html"
    context_object_name = "movements"
    paginate_by = 15

    def get_queryset(self):
        self.api_error = None
        try:
            return movements_queryset_for_request(self.request)
        except ApiError as exc:
            self.api_error = str(exc)
            return []

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["api_error"] = getattr(self, "api_error", None)
        try:
            ctx["organizations"] = get_remote_service().organizations_list()
        except ApiError as exc:
            ctx["api_error"] = ctx["api_error"] or str(exc)
            ctx["organizations"] = []
        ctx["selected_organization"] = self.request.GET.get("organization") or ""
        ctx["search_query"] = self.request.GET.get("q", "").strip()
        ctx["date_from"] = self.request.GET.get("date_from", "").strip()
        ctx["date_to"] = self.request.GET.get("date_to", "").strip()
        ctx["list_filter_query"] = movement_list_querystring(self.request)
        return ctx


class MovementExportPdfView(EcologistRequiredMixin, View):
    """
    Экспорт журнала операций в PDF (ReportLab).

    Тот же queryset, что у списка: фильтры organization и q (см. movements_queryset_for_request).
    """

    def get(self, request, *args, **kwargs):
        queryset = list(movements_queryset_for_request(request))

        try:
            font_regular, font_bold = ensure_pdf_cyrillic_fonts()
        except FileNotFoundError as exc:
            return HttpResponse(str(exc), status=500, content_type="text/plain; charset=utf-8")

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title="Операции с отходами",
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName=font_regular,
            fontSize=16,
            alignment=1,
            spaceAfter=6,
        )
        sub_style = ParagraphStyle(
            name="ReportSub",
            parent=styles["Normal"],
            fontName=font_regular,
            fontSize=10,
            alignment=1,
            textColor=colors.HexColor("#555555"),
        )

        story = []
        story.append(Paragraph("Отчёт по операциям с отходами", title_style))
        story.append(
            Paragraph(
                f"Дата формирования: {timezone.localtime(timezone.now()).strftime('%d.%m.%Y %H:%M')}",
                sub_style,
            )
        )
        story.append(Spacer(1, 14))

        header = ["Организация", "Тип отхода", "Тип операции", "Объём", "Дата"]
        table_data = [header]
        for m in queryset:
            waste_label = f"{m.waste_type.code} — {m.waste_type.name}"
            table_data.append(
                [
                    m.organization.name,
                    waste_label,
                    m.get_operation_type_display(),
                    str(m.volume),
                    m.operation_date.strftime("%d.%m.%Y"),
                ]
            )

        usable_w = doc.width
        col_widths = [
            usable_w * 0.22,
            usable_w * 0.30,
            usable_w * 0.20,
            usable_w * 0.14,
            usable_w * 0.14,
        ]
        tbl = Table(table_data, repeatRows=1, colWidths=col_widths)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6c757d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), font_bold),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("FONTNAME", (0, 1), (-1, -1), font_regular),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ]
            )
        )
        story.append(tbl)

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="operations_report.pdf"'
        return response


class MovementExportXmlView(EcologistRequiredMixin, View):
    """
    Экспорт журнала операций в XML (стандартная библиотека xml.etree.ElementTree).

    Тот же queryset, что у списка: фильтры organization и q (см. movements_queryset_for_request).
    """

    def get(self, request, *args, **kwargs):
        queryset = movements_queryset_for_request(request)
        xml_bytes = self._build_xml(queryset)

        response = HttpResponse(xml_bytes, content_type="application/xml")
        response["Content-Disposition"] = 'attachment; filename="operations_report.xml"'
        return response

    def _build_xml(self, queryset) -> bytes:
        """Формирует XML-документ с операциями движения отходов."""
        root = ET.Element("operations_report")

        ET.SubElement(root, "title").text = "Отчёт по операциям с отходами"
        ET.SubElement(root, "generated_at").text = timezone.localtime(
            timezone.now()
        ).strftime("%Y-%m-%d %H:%M:%S")

        movements_el = ET.SubElement(root, "movements")

        for movement in queryset:
            row = ET.SubElement(movements_el, "movement", id=str(movement.pk))
            ET.SubElement(row, "organization").text = movement.organization.name
            ET.SubElement(row, "waste_type").text = (
                f"{movement.waste_type.code} — {movement.waste_type.name}"
            )
            ET.SubElement(row, "operation_type").text = movement.get_operation_type_display()
            ET.SubElement(row, "volume").text = str(movement.volume)
            ET.SubElement(row, "operation_date").text = movement.operation_date.strftime(
                "%Y-%m-%d"
            )

        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)


class MovementCreateView(RemoteApiReadOnlyMixin, EcologistRequiredMixin, SuccessMessageMixin, CreateView):
    """Добавление операции."""

    model = Movement
    form_class = MovementForm
    template_name = "operations/movement_form.html"
    success_url = reverse_lazy("operations:list")
    success_message = "Операция за %(operation_date)s успешно добавлена."

    def get_readonly_redirect_url(self):
        return reverse_lazy("operations:list")


class MovementUpdateView(RemoteApiReadOnlyMixin, EcologistRequiredMixin, SuccessMessageMixin, UpdateView):
    """Редактирование операции."""

    model = Movement
    form_class = MovementForm
    template_name = "operations/movement_form.html"
    success_url = reverse_lazy("operations:list")
    success_message = "Запись об операции за %(operation_date)s обновлена."

    def get_readonly_redirect_url(self):
        return reverse_lazy("operations:list")


class MovementDeleteView(RemoteApiReadOnlyMixin, EcologistRequiredMixin, SuccessMessageMixin, DeleteView):
    """Удаление операции."""

    model = Movement
    template_name = "operations/movement_confirm_delete.html"
    success_url = reverse_lazy("operations:list")
    success_message = "Запись об операции удалена."

    def get_readonly_redirect_url(self):
        return reverse_lazy("operations:list")
