"""Presentation consumes calculation results; it never defines a separate metric."""
from collections import defaultdict
import base64
from io import BytesIO
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from studio.aggregation import compute_component, format_id, calculate
from studio.config import ordered_components
from studio.ui_filters import render_local_filters
from studio.presentation import PALETTE


def render_component(bundle, design, item, key_prefix='canvas', interactive_filters=False):
    key=(f'kpi_{item["color"][1:]}_{key_prefix}_{item["id"]}' if item['kind']=='kpi'
         else f'component_{key_prefix}_{item["id"]}')
    with st.container(border=True,key=key):
        if interactive_filters and item['local_filters'] and item['kind']!='note':
            with st.container(horizontal=True,vertical_alignment='center',gap='xsmall'):
                st.markdown(f"#### {item['title']}")
                render_local_filters(bundle,item,key_prefix)
        else:
            st.markdown(f"#### {item['title']}")
        if item['question']:
            st.caption(item['question'])
        if item['description']:
            st.caption(item['description'])
        if item['kind']=='note':
            st.write(item['note'] or 'Tambahkan penjelasan atau interpretasi pada pengaturan komponen.')
            return
        try:
            result=compute_component(bundle,design,item)
            if result.rows==0:
                st.info('Tidak ada data sesuai filter')
            elif item['kind']=='kpi':
                unit='%' if item['method']=='percentage' else item['unit']
                st.metric(item['title'],format_id(result.total,item['decimals'],unit),label_visibility='collapsed')
                if result.unavailable:
                    st.caption(result.unavailable)
            elif item['kind']=='pivot':
                render_pivot_table(result,item)
                render_pivot_chart(bundle,result,item,key_prefix)
            elif result.table.empty or result.table.Nilai.isna().all():
                st.info(result.unavailable or 'Tidak tersedia: seluruh nilai per kelompok kosong.')
            elif item['kind']=='table':
                table=result.table.copy()
                unit='%' if item['method']=='percentage' else item['unit']
                table['Nilai']=table.Nilai.map(lambda x:format_id(x,item['decimals'],unit))
                st.dataframe(table,hide_index=True,width='stretch')
                st.caption('Nilai total dihitung ulang pada seluruh cakupan; nilai unik dan persentase tidak dijumlahkan dari kelompok.')
            else:
                # Derive category colors from the full baseline, so filtering
                # does not recolor a category that remains visible.
                categories=calculate(bundle.frame(item['dataset']),{'method':'count'},
                                     item['dimension'],item['granularity']).table.Kategori.tolist()
                figure=build_figure(result,item,categories)
                if figure is not None:
                    st.plotly_chart(figure,key=f"{key_prefix}_{item['id']}",width='stretch',
                                    config={'displaylogo':False,'scrollZoom':False})
            with st.expander('Definisi indikator & cakupan'):
                st.write(result.explanation)
                st.caption(f"Dataset {bundle.version} · Acuan usia {bundle.manifest['processing']['age_reference']}")
                st.caption(f"Total cakupan: {format_id(result.total,item['decimals'],'%' if item['method']=='percentage' else item['unit'])}")
        except (ValueError,KeyError,TypeError) as exc:
            st.warning(f'Komponen perlu diperiksa: {exc}')
            st.caption('Buka Rancang Dashboard → Edit, lalu pilih dataset dan kolom yang tersedia.')


def render_pivot_table(result,item):
    unit='%' if item['method']=='percentage' else item['unit']
    st.dataframe(result.table.style.format(lambda value:format_id(value,item['decimals'],unit)),width='stretch')
    st.caption('Total dihitung ulang pada record sumber; rata-rata, nilai unik, dan persentase mengikuti cakupan masing-masing.')


def render_pivot_chart(bundle,result,item,key_prefix):
    if result.cells.empty or result.cells.Nilai.isna().all():
        st.info(result.unavailable or 'Nilai sel pivot tidak tersedia untuk grafik.')
        return
    order=calculate(bundle.frame(item['dataset']),{'method':'count'},item['pivot']['column'],
                    item['pivot']['granularity']).table.Kategori.map(str).tolist()
    figure=build_pivot_figure(result,item,order)
    st.plotly_chart(figure,key=f'{key_prefix}_{item["id"]}_pivot',width='stretch',
                    config={'displaylogo':False,'scrollZoom':False})


def build_pivot_figure(result,item,series_order=None):
    """Chart the same pivot cells, excluding the recalculated margins."""
    cells=result.cells.copy()
    unit='%' if item['method']=='percentage' else item['unit']
    display=lambda value:format_id(value,item['decimals'],unit)
    cells['Tampilan']=cells.Nilai.map(display)
    series_order=list(result.table.columns[:-1]) if series_order is None else series_order
    colors={label:PALETTE[index%len(PALETTE)] for index,label in enumerate(series_order)}
    visual=item['pivot']['visualization']
    if visual=='heatmap':
        body=result.table.iloc[:-1,:-1]
        figure=go.Figure(go.Heatmap(x=body.columns.tolist(),y=body.index.tolist(),
                        z=body.apply(pd.to_numeric).to_numpy(dtype='float64',na_value=float('nan')),
                        customdata=body.map(display).to_numpy(),colorscale='Viridis',
                        hovertemplate='%{y} / %{x}<br>%{customdata}<extra></extra>',hoverongaps=False))
        figure.update_xaxes(title=item['pivot']['column'])
        figure.update_yaxes(title=item['dimension'],autorange='reversed')
    else:
        horizontal=visual=='hbar'
        figure=px.bar(cells,x='Nilai' if horizontal else 'Baris',y='Baris' if horizontal else 'Nilai',
                       color='Kolom',orientation='h' if horizontal else 'v',
                       barmode='relative' if visual=='stacked' else 'group',custom_data=['Tampilan'],
                       color_discrete_map=colors,category_orders={'Baris':list(result.table.index[:-1]),'Kolom':series_order},
                       labels={'Baris':item['dimension'],'Kolom':item['pivot']['column'],'Nilai':unit or 'Nilai'})
        figure.update_traces(hovertemplate=('%{y}' if horizontal else '%{x}')+'<br>%{customdata[0]}<extra>%{fullData.name}</extra>')
        figure.update_layout(legend=dict(orientation='h',y=-.25,x=0))
    figure.update_layout(height=350,margin=dict(l=8,r=8,t=12,b=40),paper_bgcolor='rgba(0,0,0,0)',
                         plot_bgcolor='rgba(0,0,0,0)',font=dict(family='Arial',size=12,color='#324C40'),separators=',.')
    return figure


def build_figure(result,item,category_order=None):
    table=result.table.copy()
    # Keep missing values in the table; never coerce absent measurements to zero.
    unit='%' if item['method']=='percentage' else item['unit']
    table['Tampilan']=table.Nilai.map(lambda x:format_id(x,item['decimals'],unit))
    palette=list(PALETTE)
    category_order=table.Kategori.tolist() if category_order is None else category_order
    color_map={category:palette[index%len(palette)] for index,category in enumerate(category_order)}
    colors=[color_map.get(category,palette[0]) for category in table.Kategori]
    kind=item['kind']
    if kind in ('pie','donut'):
        if item['method'] not in ('count','count_filled','sum'):
            st.warning('Pie/donut membutuhkan ukuran bagian yang dapat dijumlahkan. Pilih jumlah baris, nilai terisi, atau penjumlahan; gunakan batang untuk rata-rata/persentase/nilai unik.')
            return None
        if (table.Nilai.dropna()<0).any() or table.Nilai.sum()<=0:
            st.info('Pie/donut membutuhkan nilai nonnegatif dengan total lebih dari nol.')
            return None
        figure=px.pie(table,names='Kategori',values='Nilai',hole=.64 if kind=='donut' else 0,
                      color_discrete_sequence=palette,custom_data=['Tampilan'])
        figure.update_traces(marker_colors=colors,textposition='inside',textinfo='percent',hovertemplate='%{label}<br>%{customdata[0]}<extra></extra>')
        figure.update_layout(legend=dict(orientation='h',y=-.12,x=0))
    elif kind=='line':
        # ISO month/year labels sort chronologically; numeric dimensions keep numeric order.
        figure=px.line(table,x='Kategori',y='Nilai',markers=True,color_discrete_sequence=[item['color']],custom_data=['Tampilan'])
        figure.update_traces(line_width=3,marker=dict(color=colors,size=8),hovertemplate='%{x}<br>%{customdata[0]}<extra></extra>',connectgaps=False)
        figure.update_layout(xaxis=dict(type='category' if item['granularity']!='category' else '-'))
    else:
        horizontal=kind=='hbar'
        figure=px.bar(table,x='Nilai' if horizontal else 'Kategori',y='Kategori' if horizontal else 'Nilai',
                      orientation='h' if horizontal else 'v',color_discrete_sequence=palette,custom_data=['Tampilan'])
        figure.update_traces(hovertemplate=('%{y}' if horizontal else '%{x}')+'<br>%{customdata[0]}<extra></extra>',
                             marker_color=colors,marker_line_width=0,marker_cornerradius=4)
    figure.update_layout(height=300,margin=dict(l=8,r=8,t=12,b=25),paper_bgcolor='rgba(0,0,0,0)',
                         plot_bgcolor='rgba(0,0,0,0)',font=dict(family='Arial',size=12,color='#324C40'),
                         separators=',.',showlegend=kind in ('pie','donut'))
    if kind not in ('pie','donut'):
        figure.update_xaxes(title=None,showgrid=kind=='hbar',gridcolor='#E5E9E2')
        figure.update_yaxes(title=unit or 'Nilai',showgrid=kind!='hbar',gridcolor='#E5E9E2')
    return figure


def dashboard_header(design,bundle):
    dash=design['dashboard']
    if dash['logo']:
        st.image(BytesIO(base64.b64decode(dash['logo'])),width=76)
    st.caption(f"{dash['village'].upper()}  /  {design['group_name'] or 'KELOMPOK BELUM DIBERI NAMA'}")
    st.title(dash['title'])
    if dash['description']:
        st.write(dash['description'])
    st.caption(f"Data bersama · {bundle.version} · Acuan usia: {bundle.manifest['processing']['age_reference']}")


def render_dashboard(bundle,design,key_prefix='canvas',interactive_filters=False):
    if not design['components']:
        st.info('Belum ada komponen buatan kelompok. Buka Rancang Dashboard lalu pilih Tambah Komponen. Contoh dashboard hanya ditampilkan di Beranda.')
        return
    rows=defaultdict(list)
    for item in ordered_components(design):
        rows[item['row']].append(item)
    count=design['dashboard']['columns']
    displayed_sections=set()
    def render_row(items):
        widths=[min(item['span'],count) for item in items]
        if sum(widths)<count:
            widths.append(count-sum(widths))
        slots=st.columns(widths,gap='medium')
        for slot,item in zip(slots,items):
            with slot:
                render_component(bundle,design,item,key_prefix=key_prefix,interactive_filters=interactive_filters)
    for items in rows.values():
        for item in items:
            if item['section'] and item['section'] not in displayed_sections:
                st.subheader(item['section'])
                displayed_sections.add(item['section'])
        current=[]
        used=0
        for item in items:
            width=min(item['span'],count)
            if used+width>count:
                render_row(current)
                current=[]
                used=0
            current.append(item)
            used+=width
        if current:
            render_row(current)
