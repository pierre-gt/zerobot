#!/usr/bin/python
# -*- coding: utf-8  -*-

"""
Statistiques fixes dans la section [[#Aujourd.27hui.2C_dans_Wikip.C3.A9dia|#Aujourd'hui, dans Wikipédia]] du bistro du jour.
Voir cette discussion :
	http://fr.wikipedia.org/w/index.php?oldid=77299088#Stat.E2.80.99_globales_live
"""

#
# (C) Framawiki, 2019
# (C) Toto Azéro, 2012-2013
#
# Distribué sous licence GNU GPLv3
# Distributed under the terms of the GNU GPLv3 license
# http://www.gnu.org/licenses/gpl.html
#
__version__ = '$Id: stats_bistro.py 120 2019-09-07 Framawiki $'
#

import _errorhandler
import pywikibot
from pywikibot import config, page, textlib
import locale, re
from datetime import datetime
import complements


def main():
	locale.setlocale(locale.LC_ALL, 'fr_FR.utf8')

	site = pywikibot.Site()
	now = datetime.now()

	page = pywikibot.Page(site, "Wikipédia:Le Bistro/%i %s" % (int(now.strftime("%d")), now.strftime("%B %Y").decode('utf-8')))

	text = page.get()
	text_part = text[text.index("\n== Aujourd'hui, dans Wikipédia =="):]
	text_part_old = text_part
	text_part = text_part.replace("Actuellement, Wikipédia compte", "Le ~~~~~, Wikipédia comptait")
	text_part = text_part.replace("{{NUMBEROFARTICLES}}", "{{subst:NUMBEROFARTICLES}}")
	text_part = text_part.replace("{{Nombre d'articles de qualité}}", "{{subst:formatnum:{{subst:#expr:{{subst:PAGESINCATEGORY:Article de qualité|R}}-3}}}}")
	text_part = text_part.replace("{{Nombre de bons articles}}", "{{subst:formatnum:{{subst:#expr:{{subst:PAGESINCATEGORY:Bon article|R}}-3}}}}")
	text_part = text_part.replace("{{Nombre d'articles géolocalisés sur Terre}}", "{{subst:formatnum:{{subst:#expr:{{subst:PAGESINCATEGORY:Article géolocalisé sur Terre|R}}}}}}")
	text_part = text_part.replace("{{Wikipédia:Le Bistro/Labels}}", "{{subst:Wikipédia:Le Bistro/Labels}}")
	text_part = text_part.replace("{{Wikipédia:Le Bistro/Test}}", "{{subst:Wikipédia:Le Bistro/Test}}")

	text = text.replace(text_part_old, text_part)

	page.put(text, comment = "Bot: Substitution des modèles afin de rendre fixes les statistiques fixes dans la section [[#Aujourd.27hui.2C_dans_Wikip.C3.A9dia|#Aujourd'hui, dans Wikipédia]]")


if __name__ == '__main__':
    try:
        main()
    except Exception as myexception:
        _errorhandler.handle(myexception)
        raise
    finally:
        pywikibot.stopme()
