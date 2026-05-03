def safe_chart_multi(workbook, worksheet, pos, title, rows, categories, series_defs,
                     line_defs=None, scale=(1,1), chart_type='column', stacked=False,
                     legend_pos='top', y_axis=None, y2_axis=None):
    """
    Chart aman multi-series (stacked bar/area + optional line combine).
    """
    chart_conf = {'type': chart_type}
    if stacked:
        chart_conf['subtype'] = 'stacked'

    chart = workbook.add_chart(chart_conf)
    chart.set_title({'name': title})
    chart.set_legend({'position': legend_pos})

    if rows and categories and series_defs:
        for s in series_defs:
            opts = {
                'name': s['name'],
                'categories': categories,
                'values': s['values'],
            }
            for opt in ('fill','line','data_labels','smooth','y2_axis'):
                if opt in s:
                    opts[opt] = s[opt]
            chart.add_series(opts)
    else:
        # dummy jika kosong
        dummy_row = worksheet.dim_rowmax + 1 if worksheet.dim_rowmax != -1 else 200
        worksheet.write(dummy_row, 0, "No Data")
        worksheet.write(dummy_row, 1, 0)
        chart.add_series({
            'name': "No Data",
            'categories': [worksheet.get_name(), dummy_row, 0, dummy_row, 0],
            'values': [worksheet.get_name(), dummy_row, 1, dummy_row, 1],
        })

    # handle line combine
    if rows and categories and line_defs:
        line_chart = workbook.add_chart({'type': 'line'})
        for s in line_defs:
            opts = {
                'name': s['name'],
                'categories': categories,
                'values': s['values'],
            }
            for opt in ('fill','line','data_labels','smooth','y2_axis'):
                if opt in s:
                    opts[opt] = s[opt]
            line_chart.add_series(opts)
        chart.combine(line_chart)

    # set axis jika ada
    if y_axis:
        chart.set_y_axis(y_axis)
    if y2_axis:
        chart.set_y2_axis(y2_axis)

    # ====== Tambahkan X-axis miring 45° ======
    chart.set_x_axis({
        'name': 'Date',
        'num_font': {'rotation': 45, 'bold': True,'size': 10, 'color': '#4b5563'},
        'name_font': {'bold': True, 'size': 11},
        'interval_unit': 1
    })

    worksheet.insert_chart(pos, chart, {'x_scale': scale[0], 'y_scale': scale[1]})
    return chart
