# backend/chat/pdf_generator.py

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI
import matplotlib.pyplot as plt
import io
import os


class PDFReportGenerator:
    """
    Generador de reportes PDF profesionales para profesores.
    Incluye estadísticas, gráficos y tablas.
    """
    
    def __init__(self, teacher, stats_data):
        """
        Args:
            teacher: Objeto CustomUser (profesor)
            stats_data: Diccionario con estadísticas del dashboard
        """
        self.teacher = teacher
        self.stats = stats_data
        self.buffer = io.BytesIO()
        self.styles = getSampleStyleSheet()
        
        # Estilos personalizados
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['BodyText'],
            fontSize=11,
            leading=14
        )
    
    def generate(self):
        """
        Genera el PDF completo y retorna los bytes.
        
        Returns:
            bytes: Contenido del PDF
        """
        # Crear documento
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Lista de elementos del PDF
        elements = []
        
        # 1. Header
        elements.extend(self._build_header())
        elements.append(Spacer(1, 0.3 * inch))
        
        # 2. Resumen Ejecutivo
        elements.extend(self._build_executive_summary())
        elements.append(Spacer(1, 0.3 * inch))
        
        # 3. Distribución de Sentimientos (con gráfico)
        elements.extend(self._build_sentiment_section())
        elements.append(Spacer(1, 0.3 * inch))
        
        # 4. Top Emociones (con gráfico)
        elements.extend(self._build_emotions_section())
        elements.append(Spacer(1, 0.3 * inch))
        
        # 5. Tabla de Estudiantes
        elements.extend(self._build_students_table())
        elements.append(Spacer(1, 0.3 * inch))
        
        # 6. Recomendaciones
        elements.extend(self._build_recommendations())
        
        # 7. Footer
        elements.extend(self._build_footer())
        
        # Construir PDF
        doc.build(elements)
        
        # Obtener bytes del PDF
        pdf_bytes = self.buffer.getvalue()
        self.buffer.close()
        
        return pdf_bytes
    
    def _build_header(self):
        """Construye el encabezado del reporte"""
        elements = []
        
        # Título
        title = Paragraph("REPORTE DE ANÁLISIS EMOCIONAL", self.title_style)
        elements.append(title)
        
        # Información del profesor y fecha
        date_str = datetime.now().strftime('%d de %B de %Y')
        info_text = f"""
        <b>Profesor:</b> {self.teacher.get_full_name() or self.teacher.username}<br/>
        <b>Email:</b> {self.teacher.email}<br/>
        <b>Fecha de generación:</b> {date_str}<br/>
        <b>Total de estudiantes:</b> {self.stats.get('total_users', 0)}
        """
        info = Paragraph(info_text, self.body_style)
        elements.append(info)
        
        # Línea separadora
        elements.append(Spacer(1, 0.2 * inch))
        
        return elements
    
    def _build_executive_summary(self):
        """Construye el resumen ejecutivo"""
        elements = []
        
        heading = Paragraph("RESUMEN EJECUTIVO", self.heading_style)
        elements.append(heading)
        
        summary_data = [
            ['Métrica', 'Valor'],
            ['Total de mensajes analizados', str(self.stats.get('total_entries', 0))],
            ['Sentimiento más común', f"{self.stats.get('most_common_sentiment', 'N/A')} ({self.stats.get('most_common_sentiment_percentage', 0)}%)"],
            ['Mensajes última semana', str(self.stats.get('entries_last_week', 0))],
        ]
        
        table = Table(summary_data, colWidths=[3.5 * inch, 2.5 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _build_sentiment_section(self):
        """Construye la sección de distribución de sentimientos con gráfico"""
        elements = []
        
        heading = Paragraph("DISTRIBUCIÓN DE SENTIMIENTOS", self.heading_style)
        elements.append(heading)
        
        sentiment_dist = self.stats.get('sentiment_distribution', [])
        
        if sentiment_dist:
            # Crear gráfico de barras
            sentiments = [item['sentiment'] for item in sentiment_dist]
            percentages = [item['percentage'] for item in sentiment_dist]
            
            fig, ax = plt.subplots(figsize=(6, 4))
            colors_map = {
                'positivo': '#2ECC71',
                'negativo': '#E74C3C',
                'neutral': '#95A5A6'
            }
            bar_colors = [colors_map.get(s.lower(), '#3498DB') for s in sentiments]
            
            ax.barh(sentiments, percentages, color=bar_colors)
            ax.set_xlabel('Porcentaje (%)', fontsize=10)
            ax.set_title('Distribución de Sentimientos', fontsize=12, fontweight='bold')
            ax.grid(axis='x', alpha=0.3)
            
            # Agregar valores en las barras
            for i, v in enumerate(percentages):
                ax.text(v + 1, i, f'{v}%', va='center', fontsize=9)
            
            plt.tight_layout()
            
            # Guardar gráfico en memoria
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()
            
            # Agregar imagen al PDF
            img = Image(img_buffer, width=5 * inch, height=3 * inch)
            elements.append(img)
        else:
            no_data = Paragraph("<i>No hay datos de sentimientos disponibles</i>", self.body_style)
            elements.append(no_data)
        
        return elements
    
    def _build_emotions_section(self):
        """Construye la sección de top emociones con gráfico"""
        elements = []
        
        heading = Paragraph("TOP 5 EMOCIONES DETECTADAS", self.heading_style)
        elements.append(heading)
        
        top_emotions = self.stats.get('top_emotions', [])
        
        if top_emotions:
            # Crear gráfico de barras horizontales
            emotions = [item['emotion'] for item in top_emotions]
            counts = [item['count'] for item in top_emotions]
            
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.barh(emotions, counts, color='#9B59B6')
            ax.set_xlabel('Cantidad de mensajes', fontsize=10)
            ax.set_title('Top 5 Emociones', fontsize=12, fontweight='bold')
            ax.grid(axis='x', alpha=0.3)
            
            # Agregar valores en las barras
            for i, v in enumerate(counts):
                ax.text(v + 0.5, i, str(v), va='center', fontsize=9)
            
            plt.tight_layout()
            
            # Guardar gráfico en memoria
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()
            
            # Agregar imagen al PDF
            img = Image(img_buffer, width=5 * inch, height=3 * inch)
            elements.append(img)
        else:
            no_data = Paragraph("<i>No hay datos de emociones disponibles</i>", self.body_style)
            elements.append(no_data)
        
        return elements
    
    def _build_students_table(self):
        """Construye la tabla de estadísticas por estudiante sin datos personales.

        Cumple la HU #9 (anonimato): no se incluyen nombres reales ni emails.
        """
        elements = []

        heading = Paragraph("ESTADÍSTICAS POR ESTUDIANTE (ANÓNIMO)", self.heading_style)
        elements.append(heading)

        users_stats = self.stats.get('users_stats', [])

        if users_stats:
            # Encabezados (sin PII)
            table_data = [['Estudiante', 'Mensajes', 'Sentimiento', 'Emoción']]

            # Datos: usar display_name provisto o enumerar como Estudiante #N
            for idx, user in enumerate(users_stats, start=1):
                display_name = user.get('display_name') or f"Estudiante #{idx}"
                table_data.append([
                    display_name,
                    str(user.get('entries_count', 0)),
                    user.get('dominant_sentiment', ''),
                    user.get('dominant_emotion', '')
                ])

            # Crear tabla
            table = Table(table_data, colWidths=[2.3 * inch, 1.0 * inch, 1.6 * inch, 1.6 * inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E67E22')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))

            elements.append(table)
        else:
            no_data = Paragraph("<i>No hay estudiantes asignados</i>", self.body_style)
            elements.append(no_data)

        return elements
    
    def _build_recommendations(self):
        """Construye la sección de recomendaciones"""
        elements = []
        
        heading = Paragraph("RECOMENDACIONES", self.heading_style)
        elements.append(heading)
        
        # Analizar datos para generar recomendaciones
        recommendations = []
        
        users_stats = self.stats.get('users_stats', [])
        negative_students = [u for u in users_stats if u['dominant_sentiment'] == 'negativo']
        
        if len(negative_students) > 0:
            recommendations.append(
                f"• <b>{len(negative_students)} estudiante(s)</b> muestran patrones de sentimiento negativo predominante. "
                "Se recomienda seguimiento individual."
            )
        
        total_entries = self.stats.get('total_entries', 0)
        entries_last_week = self.stats.get('entries_last_week', 0)
        
        if entries_last_week > 0:
            weekly_percentage = round((entries_last_week / total_entries * 100) if total_entries > 0 else 0, 1)
            recommendations.append(
                f"• El <b>{weekly_percentage}%</b> de los mensajes ocurrieron en la última semana, "
                "lo que indica participación activa reciente."
            )
        
        most_common_sentiment = self.stats.get('most_common_sentiment', '')
        if most_common_sentiment == 'positivo':
            recommendations.append(
                "• El sentimiento general es <b>positivo</b>, lo que refleja un buen clima emocional "
                "en el grupo."
            )
        elif most_common_sentiment == 'negativo':
            recommendations.append(
                "• El sentimiento general es <b>negativo</b>. Se sugiere implementar actividades "
                "de apoyo emocional grupal."
            )
        
        # Agregar recomendaciones al PDF
        if recommendations:
            for rec in recommendations:
                rec_para = Paragraph(rec, self.body_style)
                elements.append(rec_para)
                elements.append(Spacer(1, 0.1 * inch))
        else:
            no_rec = Paragraph("<i>No hay recomendaciones específicas en este momento</i>", self.body_style)
            elements.append(no_rec)
        
        return elements
    
    def _build_footer(self):
        """Construye el pie de página"""
        elements = []
        
        elements.append(Spacer(1, 0.5 * inch))
        
        footer_text = f"""
        <i>Reporte generado automáticamente por el Sistema de Análisis Emocional<br/>
        Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>
        """
        footer = Paragraph(footer_text, self.body_style)
        elements.append(footer)
        
        return elements
