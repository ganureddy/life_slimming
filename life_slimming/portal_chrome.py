"""Reviewed page chrome; leave record headings, filters and modal headers intact.

Legacy scripts still update some branding nodes by ID. Keep those nodes inert
and hidden until the corresponding source scripts are migrated.
"""
from bs4 import Comment

# source: (toolbar containers, duplicate branding/session displays)
PAGE_CHROME = {
    'accounts-command-center': ('.hdr', '.hdr .brandimg, .hdr h1'),
    'appointment-shedular': ('.pa-header', '.pa-header > div:first-child'),
    'approvals-report': ('.rhead', '.report-title-wrap, .life-homeback, .rhead .who'),
    'asset-master': ('.la-topbar', '.la-brand, .la-topbar-spacer'),
    'audit': ('', '.la-hdr'),
    'b2b-testing': ('.life-hdr', '.life-hdr > .life-logo, .life-hdr > div:nth-child(2)'),
    'branch-command-center': ('.hdr', '.hdr-left'),
    'branch-expenditure-entry': ('.life-exp-hero', '.life-exp-brand, .life-exp-clock-pill'),
    'branch-home-target': ('.btgt-head', '.btgt-title'),
    'branch-visit-report': ('.life-reports-header', '.life-reports-header > div:first-child:not(.life-header-actions)'),
    'cc-new-dashboard-bhuvan-oct2': ('.hdr', '.hdr-brand'),
    'call-center-new-report-bhuvan': ('.life-reports-header', '.life-reports-header > div:first-child:not(.life-header-actions)'),
    'cc-new-dash': ('.hdr', '.hdr-brand'),
    'client-info': ('.c3-mast', '.c3-mast-brand'),
    'client-weight-loss-info': ('.wl-header', '.wl-header > div:first-child'),
    'cluster-head-dashboard': ('.cd-top', '.cd-top > div:first-child'),
    'contols-command': ('.topbar', '.topbar > .logo, .topbar > .brand, .topbar .clock'),
    'coo-dashboard': ('.hdr', '.hdr .logo, .hdr .clk'),
    'data-correction': ('.mast', '.mast > .logo, .mast > .ttl, .mast > .user'),
    'employee-sale-master-data': ('', '.ref-header, .ref-gold-bar'),
    'enrollment-register-testing': ('.mast', '.mast > .logo, .mast > div:nth-child(2), .mast > .spacer, #userchip, .headbar > .hb-ic, .headbar > div:nth-child(2)'),
    'followup-master': ('.life-topbar', '.life-page-heading, .life-brand'),
    'glp-programme': ('.glp-mast', '.glp-title, .glp-user'),
    'hrms-dashboard---copy': ('.mast', '.mast > .logo, .mast > .ttl, .mast > .user'),
    'knowledge-centre': ('.mobtop', '.mobtop > .t'),
    'life-audit-report': ('', ''),  # Header is rendered by JavaScript; see module CSS.
    'life-master-report': ('.top', '.tlogo, .tmid, .tright'),
    'md-dashboard': ('.topbar', '.brandtxt'),
    'new-client-registration': ('', ''),  # Already has no page masthead.
    'operations-service-module': ('.lo-header', '.lo-brand'),
    'package-conversion-c2c': ('', '.c2c-p2p-header, .gold-bar'),
    'package-conversion-for-p2p': ('', '.pkg-header, .pkg-gold-bar'),
    'payables-planner': ('.mast', '.mast > .logo, .mast > .ttl, .mast > .user'),
    'pending-balances-updates': ('.pdr-hd', '.hd-row > div:first-child'),
    'price-list': ('', ''),  # These headings label individual tables.
    'sales-master-data': ('', '.rr-hdr'),
    'stock-dashboard': ('.life-stock-app-header', '.life-stock-app-brand, .life-stock-header-profile, .life-stock-header-clock'),
    'stores-360-testing-2': ('.topbar', '.brandmark, .topbar > div:nth-child(2), .tb-clock, .tb-user'),
    'task-management': ('', '.header, .gold-bar'),
    'v': ('.fad-hero', '.fad-hero-left'),
}


def prepare_chrome(soup, name):
    toolbar, branding = PAGE_CHROME.get(name, ('', ''))
    if branding:
        for tag in soup.select(branding):
            tag['data-portal-chrome'] = ''
            tag['hidden'] = ''
            tag['inert'] = ''
            tag['aria-hidden'] = 'true'
            # Some exported pages force their navigation visible with an
            # !important ID selector. Keep the DOM hooks without duplicate UI.
            tag['style'] = tag.get('style', '').rstrip('; ') + '; display: none !important;'
    if toolbar:
        for tag in soup.select(toolbar):
            if tag.name == 'header':
                tag.name = 'div'
            tag['class'] = tag.get('class', []) + ['portal-module-toolbar']
    # Export instructions and disabled copies of old headers are not runtime code.
    for comment in soup.find_all(string=lambda node: isinstance(node, Comment)):
        comment.extract()
