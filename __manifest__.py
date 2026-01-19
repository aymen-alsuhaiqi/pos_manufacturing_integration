{
    'name': 'pos_manufacturing_integration',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Integrate Manufacturing with Point of Sale',
    'description': """
    This module integrates Manufacturing with Point of Sale, allowing for
    automatic creation of Manufacturing Orders when products are sold via POS.
    """,
    'author': 'Aymen Alsuhaiqi',
    'depends': ['point_of_sale', 'mrp'],
    "data": [
        "views/mrp_production_views.xml",
        "views/product_template_views.xml"
    ],
    'installable': True,
    'application': False,
}