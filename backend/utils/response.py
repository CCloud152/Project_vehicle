from flask import jsonify


def success_response(data=None, message="操作成功"):
    """
    成功响应

    Args:
        data: 响应数据
        message: 响应消息

    Returns:
        JSON响应
    """
    response = {
        'status': 'success',
        'message': message
    }
    if data is not None:
        response['data'] = data
    return jsonify(response)


def error_response(message="操作失败", status_code=400):
    """
    错误响应

    Args:
        message: 错误消息
        status_code: HTTP状态码

    Returns:
        JSON响应
    """
    response = {
        'status': 'error',
        'message': message
    }
    return jsonify(response), status_code


def pagination_response(items, total, page=1, page_size=10):
    """
    分页响应

    Args:
        items: 数据项列表
        total: 总数据量
        page: 当前页码
        page_size: 每页大小

    Returns:
        JSON响应
    """
    return jsonify({
        'status': 'success',
        'data': items,
        'pagination': {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
    })
