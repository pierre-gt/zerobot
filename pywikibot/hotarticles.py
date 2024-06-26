#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Met à jour les modèles {{User:ZéroBot/Articles chauds}}.
"""
#
# (C) Framawiki, 2018-2019
# (C) Toto Azéro, 2016
# (C) Ryan Kaldari, 2013-2015
#
# Distribué sous licence GNU AGPLv3
# Distributed under the terms of the GNU AGPLv3 license
# http://www.gnu.org/licenses/gpl.html
#
__version__ = '$Id: hotarticles.py 0100 2019-07-20 20:17:00 (UTC) Framawiki $'
#

from maj_articles_recents import check_and_return_parameter
from pywikibot import pagegenerators, config, textlib
import _errorhandler
import pywikibot
import pickle
import os
import pymysql
import time
import datetime
import traceback


def encode_sql(string):
        return string.replace('"', '\\"').replace("'", "\\'").replace(' ', '_')

def page_to_string(page, asLink = False, withNamespace=False):
        return encode_sql(page.title(as_link = asLink, with_ns = withNamespace))

def decode_sql(string, remove_underscores=True):
        string=string.decode('utf-8')
        if remove_underscores:
                string = string.replace('_', ' ')
        return string

class BotArticlesChauds():
        def __init__(self, main_page, modele, dry=False):
                self.site = pywikibot.Site()
                self.main_page = main_page
                self.modele = modele
                self.dry = dry

                self.matchDebut = "<!-- Ce tableau est créé automatiquement par un robot. Articles Chauds DEBUT -->"
                self.matchFin = "\n<!-- Ce tableau est créé automatiquement par un robot. Articles Chauds FIN -->"

                self.cat = None
                self.nbMax = None
                self.minimum = None
                self.delai = None
                self.orange = None
                self.rouge = None
                self.actions = None
                self.mineures = None
                self.contributeurs = None
                self.minimum_contributeurs = None
                self.bots_inclus = None
                self.bots_inclus_str = None
                self.transclusion = None
                self.diff = None
                self.lien_historique = None

                self.comment = 'Bot: Mise à jour des articles chauds'

        def get_params(self):
                text = self.main_page.get()

                templates = textlib.extract_templates_and_params(text)
                template_in_use = None
                for tuple in templates:
                        if tuple[0] == modele.title(as_link=False):
                                template_in_use = tuple[1]
                                break

                if not template_in_use:
                        _errorhandler.message("Aucun modèle {{%s}} détecté sur la page" % modele.title(asLink=False), addtags={'page': self.main_page})
                        return False

                titre_categorie = check_and_return_parameter(template_in_use, 'catégorie')
                if not titre_categorie:
                        return False
                self.cat = pywikibot.Category(site, titre_categorie)
                if not self.cat.exists():
                        _errorhandler.message("Erreur : la catégorie n'existe pas", addtags={'page': self.main_page})
                        return False

                self.nbMax = check_and_return_parameter(template_in_use, 'nbMax', -1)
                try:
                        self.nbMax = int(self.nbMax)
                except:
                        _errorhandler.message('Erreur : nbMax incorrect', addtags={'page': self.main_page})
                        return False

                self.minimum = check_and_return_parameter(template_in_use, 'minimum', '10')
                try:
                        self.minimum = int(self.minimum)
                except:
                        _errorhandler.message('Erreur : minimum incorrect', addtags={'page': self.main_page})
                        return False

                self.actions = check_and_return_parameter(template_in_use, 'actions', '0,1,3')
                try:
                        [int(k) for k in self.actions.split(',')]
                except:
                        _errorhandler.message('Erreur : des actions spécifiées ne sont pas des entiers', addtags={'page': self.main_page})
                        return False

                self.delai = check_and_return_parameter(template_in_use, 'délai', '7')
                try:
                        self.delai = int(self.delai)
                        if self.delai <= 0:
                                _errorhandler.message('Erreur : délai négatif', addtags={'page': self.main_page})
                                return False
                except:
                        _errorhandler.message('Erreur : délai incorrect', addtags={'page': self.main_page})
                        return False

                self.orange = check_and_return_parameter(template_in_use, 'limite_orange', '20')
                try:
                        self.orange = int(self.orange)
                except:
                        _errorhandler.message('Erreur : orange incorrect', addtags={'page': self.main_page})
                        return False

                self.rouge = check_and_return_parameter(template_in_use, 'limite_rouge', '40')
                try:
                        self.rouge = int(self.rouge)
                except:
                        _errorhandler.message('Erreur : rouge incorrect', addtags={'page': self.main_page})
                        return False

                self.mineures = check_and_return_parameter(template_in_use, 'mineures', '0')
                try:
                        self.mineures = int(self.mineures)
                except:
                        _errorhandler.message('Erreur : mineures incorrect', addtags={'page': self.main_page})
                        return False

                self.contributeurs = check_and_return_parameter(template_in_use, 'contributeurs', '0')
                try:
                        self.contributeurs = int(self.contributeurs)
                except:
                        _errorhandler.message('Erreur : contributeurs incorrect', addtags={'page': self.main_page})
                        return False

                self.minimum_contributeurs = check_and_return_parameter(template_in_use, 'minimum_contributeurs', '1')
                try:
                        self.minimum_contributeurs = int(self.minimum_contributeurs)
                except:
                        _errorhandler.message('Erreur : minimum_contributeurs incorrect', addtags={'page': self.main_page})
                        return False

                self.bots_inclus = check_and_return_parameter(template_in_use, 'bots_inclus', '1')
                try:
                        self.bots_inclus = int(self.bots_inclus)
                except:
                        _errorhandler.message('Erreur : bots_inclus incorrect', addtags={'page': self.main_page})
                        return False

                self.bots_inclus_str = ''
                if self.bots_inclus == 0: # ne pas prendre les bots en compte
                        # rc_bot indique une modification faite par un bot
                        self.bots_inclus_str = 'AND rc_bot = 0'

                self.transclusion = check_and_return_parameter(template_in_use, 'transclusion', '0')
                try:
                        self.transclusion = int(self.transclusion)
                except:
                        _errorhandler.message('Erreur : transclusion incorrect', addtags={'page': self.main_page})
                        return False

                self.diff = check_and_return_parameter(template_in_use, 'diff', '0')
                try:
                        self.diff = int(self.diff)
                except:
                        _errorhandler.message('Erreur : diff incorrect', addtags={'page': self.main_page})
                        return False

                self.lien_historique = check_and_return_parameter(template_in_use, 'lien_historique', '0')
                try:
                        self.lien_historique = int(self.lien_historique)
                except:
                        _errorhandler.message('Erreur : diff incorrect', addtags={'page': self.main_page})
                        return False

                self.namespaces = check_and_return_parameter(template_in_use, 'namespaces', '0')
                print(self.namespaces)
                try:
                        # Check namespaces specified are actually numbers,
                        # and preformat them for the SQL request
                        self.namespaces = "(" + ",".join([str(int(k)) for k in self.namespaces.split(",")]) + ")"
                except:
                        _errorhandler.message('Erreur : namespaces incorrect', addtags={'page': self.main_page})
                        return False

                return True

        def build_table(self):
                frwiki_p = pymysql.connect(host='frwiki.analytics.db.svc.wikimedia.cloud', database='frwiki_p', read_default_file="/data/project/naggobot/replica.my.cnf", cursorclass=pymysql.cursors.DictCursor)
                cursor=frwiki_p.cursor()
                cursor.execute("SELECT s.rev_id, s.rev_timestamp FROM revision AS s \
                WHERE s.rev_timestamp > DATE_FORMAT(DATE_SUB(NOW(), INTERVAL %i DAY),'%%Y%%m%%d%%H%%i%%s') \
                ORDER BY s.rev_timestamp ASC LIMIT 1;" % self.delai)
                result = cursor.fetchone()
                rev_timestamp = int(result['rev_timestamp'])
                rev_id = int(result['rev_id'])

                query = "SELECT page_id, page_title, COUNT(*) AS count_changes, SUM(rc_minor) \
AS count_minor, COUNT(DISTINCT rc_actor) as nb_users, SUM(COALESCE(rc_new_len, 0) - COALESCE(rc_old_len, 0)) as diff \
FROM recentchanges \
JOIN (SELECT page_id, page_title FROM categorylinks \
JOIN page ON page_id=cl_from AND page_namespace IN %(namespaces)s \
WHERE cl_to='%(category)s' AND page_latest > %(rev_id)i) AS main \
ON rc_cur_id=page_id \
WHERE rc_timestamp>%(rev_timestamp)i AND rc_type IN (%(actions)s) %(bots_inclus_str)s \
GROUP BY page_id HAVING count_changes >= %(limit)i AND nb_users >= %(minimum_contributeurs)i \
ORDER BY count_changes DESC;" % {
        'category':page_to_string(self.cat), \
        'rev_id':rev_id, 'rev_timestamp':rev_timestamp, \
        'limit':self.minimum, 'actions':self.actions, \
        'minimum_contributeurs':self.minimum_contributeurs, \
        'bots_inclus_str':self.bots_inclus_str, \
        'namespaces': self.namespaces}
                _errorhandler.log_context(query, category='sql')

                if self.nbMax > 0:
                        query = query[:-1] + " LIMIT %i;" % self.nbMax

                cursor.execute(query)
                text = ""

                # Il peut ne pas être nécessaire d'effectuer les transclusions
                # si le nombre de résultats n'excède par le paramètre transclusion
                # renseigné.
                results=cursor.fetchall()
                if self.transclusion and len(results) > self.transclusion:
                        do_transclude = True
                else:
                        do_transclude = False

                if do_transclude:
                        text += "<onlyinclude>"

                text += "{|"
                for i in range(len(results)):
                        if do_transclude and i == self.transclusion:
                                # on vient d'atteindre le nombre de transclusions
                                text += "</onlyinclude>"

                        result = results[i]
                        count = int(result['count_changes'])
                        count_minor = int(result['count_minor'])
                        page = result['page_title']
                        nb_users = result['nb_users']
                        diff_value = result['diff']

                        color = ''
                        if count > self.rouge:
                                color = "#c60d27"
                        elif count > self.orange:
                                color = "#f75a0d"
                        else:
                                color = "#ff9900"

                        diff_str = ''
                        if self.diff:
                                signe = ''
                                gras = ""
                                if diff_value > 0:
                                        classe = "mw-plusminus-pos"
                                        signe = '+'
                                elif diff_value < 0:
                                        classe = "mw-plusminus-neg"
                                        # signe - déjà présent
                                else:
                                        classe = "mw-plusminus-null"

                                if abs(diff_value) >= 500:
                                        gras = "'''"

                                diff_str = ' <span class="(classe)s">%(gras)s(%(signe)s{{formatnum:%(diff_value)i}})%(gras)s</span>' % {'classe':classe, \
                                        'signe':signe, 'gras':gras, 'diff_value':diff_value}

                        actions_str = """'''%i'''&nbsp;<span style="font-size:60%%">actions</span>""" % count
                        if self.lien_historique:
                                actions_str = "[//fr.wikipedia.org/w/index.php?title=" + decode_sql(page, remove_underscores=False) + \
                                        "&action=history" + actions_str + "]"

                        if self.mineures and self.contributeurs:
                                text += """\n|-
| style="text-align:center; font-size:130%%; color:white; background:%(color)s; padding: 0 0.2em" | %(actions_str)s
| rowspan="3" style="padding: 0.4em;" | [[%(page)s]]%(diff)s
|-
| style="text-align:center; font-size:65%%; color:white; background:%(color)s; padding: 0 0.2em" | ('''%(count_minor)i'''&nbsp;mineures)
|-
| style="text-align:center; font-size:65%%; color:white; background:%(color)s; padding: 0 0.2em" | ('''%(nb_users)i'''&nbsp;contributeurs)
|-
|""" % {'color':color, 'actions_str':actions_str, 'page':decode_sql(page), 'count_minor':count_minor, 'nb_users':nb_users, 'diff':diff_str}
                        elif self.contributeurs:
                                text += """\n|-
| style="text-align:center; font-size:130%%; color:white; background:%(color)s; padding: 0 0.2em" | %(actions_str)s
| rowspan="2" style="padding: 0.4em;" | [[%(page)s]]%(diff)s
|-
| style="text-align:center; font-size:65%%; color:white; background:%(color)s; padding: 0 0.2em" | ('''%(nb_users)i'''&nbsp;contributeurs)
|-
|""" % {'color':color, 'actions_str':actions_str, 'page':decode_sql(page), 'nb_users':nb_users, 'diff':diff_str}
                        elif self.mineures:
                                text += """\n|-
| style="text-align:center; font-size:130%%; color:white; background:%(color)s; padding: 0 0.2em" | %(actions_str)s
| rowspan="2" style="padding: 0.4em;" | [[%(page)s]]%(diff)s
|-
| style="text-align:center; font-size:65%%; color:white; background:%(color)s; padding: 0 0.2em" | ('''%(count_minor)i'''&nbsp;mineures)
|-
|""" % {'color':color, 'actions_str':actions_str, 'page':decode_sql(page), 'count_minor':count_minor, 'diff':diff_str}
                        else:
                                text += """\n|-
| style="text-align:center; font-size:130%%; color:white; background:%(color)s; padding: 0 0.2em" | %(actions_str)s
| style="padding: 0.4em;" | [[%(page)s]]%(diff)s""" % {'color':color, 'actions_str':actions_str, \
                                               'page':decode_sql(page), 'diff':diff_str}

                text += "\n"

                if do_transclude:
                        text += "<onlyinclude>\n"

                text += "|}"

                if do_transclude:
                        text += "</onlyinclude>"

                return text

        def edit_page(self):
                text = self.main_page.get()

                # Définition d'une nouvelle variable pour éviter toute suppression
                # involontaire dans text.
                new_text = text[:text.index(self.matchDebut)]
                new_text += self.matchDebut
                new_text += "\n"
                new_text += self.build_table()
                new_text += self.matchFin
                try:
                        new_text += text[text.index(self.matchFin)+len(self.matchFin):]
                except ValueError:
                        _errorhandler.message('Tags not found in page content', addtags={'page': self.main_page.title()})
                        return

                if not self.dry:
                        page.put(new_text, self.comment)
                        return True
                else:
                        pywikibot.output(new_text)

        def run(self):
                pywikibot.output("\n=== Doing page %s ===" % self.main_page.title())
                if not self.get_params():
                        pywikibot.output("Erreur lors de la récupération des paramètres")
                        return False

                return self.edit_page()

if __name__ == '__main__':
        try:
                # parser des arguments
                dry = False
                test = False
                gen = []
                for arg in pywikibot.handle_args():
                        if arg == "-dry":
                                dry = True
                                pywikibot.output('(dry is ON)')

                        elif arg[0:6] == "-test:":
                                titre_page_test = arg[6:]
                                gen.append(titre_page_test)

                                # pour afficher la mention uniquement
                                # la première fois que l'argument est rencontré
                                if not test:
                                        pywikibot.output('(test is ON)')
                                test = True

                site = pywikibot.Site()
                titre_modele = "Utilisateur:ZéroBot/Articles chauds"
                modele = pywikibot.Page(site, titre_modele)#, ns = 10)
                cat = pywikibot.Category(site, "Catégorie:Page mise à jour par un bot/Articles chauds")


                # le générateur a été créé via la lecture des arguments
                # dans le cas où le mode test est actif.
                if not test:
                        #gen = pagegenerators.ReferringPageGenerator(modele, onlyTemplateInclusion = True)
                        gen = cat.articles()
                else:
                        gen = [pywikibot.Page(site, titre) for titre in gen]

                for page in gen:
                        try:
                                bot = BotArticlesChauds(page, modele, dry)
                                if not bot.run():
                                        pywikibot.output('Page %s not done' % page.title())
                        except Exception as ex:
                                pywikibot.output("Error occurred while doing page %s" % page.title())
                                _errorhandler.handle(ex, fatal=False, addtags={'page': page})
        except Exception as ex:
                if not (test or dry):
                        _errorhandler.handle(ex)
                raise
        finally:
                pywikibot.stopme()
