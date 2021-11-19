#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Ajoute ou tente de corriger les dates à indiquer dans certains modèles.

TODO : code moche, tout ré-écrire

Dernières modifications :
* 0210 : gestion du cas de la révision supprimée
* 0200 : rechercher la date d'ajout du modèle
* 0172 : correction des dates avec des jours
* 0170 : correction des expressions regex créée de manière automatisée
* 0167 : correction gestion paramètres
* 0166 : gestion du modèle {{Section à délister}}
* 0165 : espace de noms principal seulement, gestion de nouveaux modèles
* 0162 : gestion du modèle {{Vérifiabilité}}
* 0161 : gestion du modèle {{Vérifiabilité}}
* 0160 : gestion du modèle {{Article sans source}}
* 0159 : correction erreur unicode + adaptation aux Labs
"""
#
# (C) Toto Azéro, 2013-2017
# (C) Framawiki, 2018
#
# Distribué sous licence GNU GPLv3
# Distributed under the terms of the GNU GPLv3 license
# http://www.gnu.org/licenses/gpl.html
#
__version__ = '$Id: modeles_sans_dates.py 0210 2018-06-24 22:43:59 (CEST) Framawiki $'
#

from pywikibot import textlib
import pywikibot
import _errorhandler
import re, time, datetime
import locale

class BotPrecisionModele:
	def __init__(self):
		self.titres_modeles_initiaux = ["À sourcer", "Admissibilité à vérifier", "À wikifier", \
			"Article sans source", "Vérifiabilité", "Orphelin", "Guide pratique", "Section guide pratique", \
			"Section guide pratique", "Section à wikifier", "Section à sourcer", "Section à délister", \
			"BPV à sourcer", "À illustrer", "Section à sourcer", "Sources secondaires", "Sources à lier", \
			"Internationaliser", "À mettre à jour", "À recycler", "Source unique", \
			"Traduction à revoir", "Travail inédit", "Style non encyclopédique", "Style non encyclopédique section", \
			"Trop d'ouvrages", "Résumé introductif", "Désaccord de neutralité", "Traduction incomplète", \
			"Rédaction", "Anecdotes", "Trop de liens", "À dater", "À délister", "Désaccord de neutralité", \
			"Pertinence section", "À vérifier", "Section non neutre", "Rédaction", "Trop d'ouvrages", \
			"À déjargoniser", "Promotionnel", "Article incomplet", "À vérifier/architecture", "Trop long", \
			"Article non neutre", "Conventions bibliographiques", "Section trop longue", "À recycler/droit", \
			"Section à recycler", "À recycler/biographie", "À recycler/catch", "À recycler/géographie", \
			"À recycler/histoire militaire", "À recycler/judaïsme", "À recycler/mathématiques", \
			"À recycler/récompenses", "À recycler/zoologie", \
			"À vérifier/alimentation", "À vérifier/anthropologie", "À vérifier/architecture", \
			"À vérifier/association", "À vérifier/astronomie", "À vérifier/biographie", "À vérifier/biologie", \
			"À vérifier/botanique", "À vérifier/chimie", "À vérifier/cinéma", "À vérifier/criminologie", \
			"À vérifier/culture", "À vérifier/danse", "À vérifier/droit", "À vérifier/entreprise", \
			"À vérifier/environnement", "À vérifier/généalogie", "À vérifier/géographie", "À vérifier/géologie", \
			"À vérifier/hip-hop", "À vérifier/histoire", "À vérifier/histoire militaire", "À vérifier/informatique", \
			"À vérifier/jeu vidéo", "À vérifier/linguistique", "À vérifier/littérature", "À vérifier/mathématiques", \
			"À vérifier/mode", "À vérifier/musique", "À vérifier/mythologie", "À vérifier/médecine", \
			"À vérifier/média", "À vérifier/paléontologie", "À vérifier/peinture", "À vérifier/philosophie", \
			"À vérifier/physique", "À vérifier/politique", "À vérifier/psychologie", "À vérifier/religion", \
			"À vérifier/sciences", "À vérifier/sociologie", "À vérifier/sport", "À vérifier/transports", \
			"À vérifier/télévision", "À vérifier/zoologie", "À vérifier/économie", "À vérifier/éducation", \
			"Plan", "Sources obsolètes", "Typographie", "Catalogue de vente", "Hagiographique", "CV", \
			"À prouver", "À désacadémiser", "Pertinence", "Copyvio", "À délister", "Section à recycler", \
			"Résumé introductif trop long", "Vie privée", "à recycler/histoire militaire", "pour wikiquote", \
			"trop de citations", "Anthropocentrisme", "Résumé introductif trop court",
			"Section trop compacte", "Orthographe", "Délister", "Article mal proportionné"]
		self.site = pywikibot.Site()
		self.liste_titres_cats = ["Admissibilité à vérifier, date manquante", "Article à wikifier, date manquante", \
			"Article sans source, date manquante", "Article non vérifiable, date manquante", \
			"Article orphelin, date manquante", "Guide pratique, date manquante", \
			"Article manquant de références depuis date inconnue", "Article avec section à délister, date manquante", \
			"Bandeau de maintenance sans paramètre date", "Bandeau de maintenance sans paramètre date/Liste complète"]
		#u"Article avec section à wikifier, date manquante"

	def generate_liste_pages_modele(self, modeles):
		"""
		Génère la liste complète des modèles utilisables (redirections comprises)
		"""
		liste_titres = []
		for titre_modele in modeles:
			page = pywikibot.Page(self.site, titre_modele, ns=10)
			while page.isRedirectPage():
				page = page.getRedirectTarget()
			liste_titres.append(page)
			liste_titres_redirect = [p for p in page.backlinks(filter_redirects=True)]
			# ex : liste_titres_redirect =
			#			[u'Sources', u'A sourcer', u'Source ?']
			liste_titres.extend(liste_titres_redirect)

		return liste_titres

	def find_add(self, page, modele):
		"""
		modele is a pywikibot.Page
		"""
		site = pywikibot.Site()

		unblock_found = True
		history = page.revisions()

		pywikibot.output("Analysing page %s" % page.title())
#		if len(history) == 1:
#			[(id, timestamp, user, comment)] = history
#			return (timestamp, id)
		if page.revision_count() == 1:
			rev=next(history)
			timestamp = rev['timestamp']
			id = rev['revid']
			return (timestamp, id)

		oldid = None
		requester = None
		timestamp_add = None
		look_back_count = 2
		look_back = look_back_count

		for rev in history:
			user = rev['user']
			comment = rev['comment']
			timestamp = rev['timestamp']
			id = rev['revid']

			pywikibot.output("Analyzing id %i: timestamp is %s and user is %s" % (id, timestamp, user+(" (lookback)" if look_back < look_back_count else "")))
			if not user:
				pywikibot.output("User's missing (hidden?), skipping this version...")
				continue

			text = page.getOldVersion(id)
			if not text:
				pywikibot.output("Can't get rev text (hidden?), skipping this version...")
				continue
			# text might be too long, if so textlib.extract_templates_and_params won't
			# proceed and will skip some templates
			#if u"{{déblocage" in text.lower():
			#	text = text[max(0,text.lower().index(u"{{déblocage")-12):]

			templates_params_list = textlib.extract_templates_and_params(text)
			unblock_found = False
			for (template_name, dict_param) in templates_params_list:
				try:
					template_page = pywikibot.Page(pywikibot.Link(template_name, site, defaultNamespace=10), site)
					# TODO : auto-finding redirections
					if template_page == modele:
						#pywikibot.output((template_name, dict_param))
						unblock_found = True
						look_back = look_back_count
						break
				except Exception as myexception:
					pywikibot.output('An error occurred while analyzing template %s' % template_name)
					pywikibot.output('%s %s'% (type(myexception), myexception.args))

			#if oldid:
			#	print("oldid is %i" % oldid)
			#else:
			#	print "no oldid"
			if (not unblock_found and id == oldid):
				# We did not find the model we were looking for
				# in the most recent revision: abort
				pywikibot.output("Last revision does not contain any {{modele}} template!")
				return None
			elif not unblock_found:
				# We did not find the model we are looking for
				# in some old revision, but it was present in
				# more recent ones.
				# We will snap back at look_back revisions, to check
				# whether the model was truly added in the current
				# revision or if it dates back to some older revision
				# and was simply removed heer due to eg. vandalism
				if look_back > 0:
					pywikibot.output("Template was added in oldid https://fr.wikipedia.org/w/index.php?oldid=%i" % oldid)
					return (timestamp_add, oldid)
				else:
					# Look back another time, but don't change
					# the future value returned (requested, oldid
					# timestamp_add)
					look_back -= 1
			else:
				requester = pywikibot.User(site, user)
				oldid = id
				timestamp_add = timestamp

		# Si on arrive là, c'est que la première version de la page contenait déjà le modèle
		return (timestamp, id)

	def operate(self, page, liste_modeles):
		dict = {}
		modeles_modifies_str = ""
		count_modeles_modifies = 0
		add_date = False

		pywikibot.output("Doing page %s" % page)
		if page.isRedirectPage():
			pywikibot.output("Page is a redirection, skipping.")
			return
		text = page.get()
		old_text = text

		for couple in page.templatesWithParams():
			#print couple
			for modele in liste_modeles:
				if couple[0]==modele:
					dict[modele] = couple[1]

		for modele in dict:
		# NB : modele est de type pywikibot.Page
			titre_modele = modele.title(with_ns=False)

			add_date = True
			change_date = False
			re_params = ""
			#str_params = u""
			#pywikibot.output(u"modele : %s" % modele.title(withNamespace=False))
			if dict[modele]:
				for param in dict[modele]:
					param = param.replace('(', '\(').replace(')', '\)').replace('[', '\[').replace(']', '\]').replace('{', '\{').replace('{', '\}').replace('?', '\?').replace('|', '\|').replace('*', '\*').replace('+', '\+')
					#param = re.escape(param)
					re_params += (" *\| *([0-9]+ *= *)?%s" % param) # Paramètres allant avec le modèle
					#str_params += u"|%s" % param
					if re.search("^date *=.+", param):
						param_date = re.search("^date *= *([0-9]{0,2}) *(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre) *(20[0-9]{2})", param)
						add_date = False
						if param_date and param_date.group(1):
							text = text.replace(param_date.group(0), "date=%s %s" % (param_date.group(2), param_date.group(3)))

						# NB : ne fait rien si un paramètre date est mal renseigné
						# mais que la correction à appliquer est inconnue, pour éviter
						# d'ajouter une fausse date.
						#   ex : quelqu'un ajoute 'date=octobr 2015' après recherche
						#		 mais le script tourne en janvier 2016 donc le bot
						#		 effacerait l'ancienne date pour rajouter une date
						# 		 incorrecte.

			#pywikibot.output("add_date = %s" % unicode(add_date))
			#pywikibot.output("str_params = %s" % unicode(str_params))
			#pywikibot.output("re_params = %s" % unicode(re_params))

			if add_date:
				# Permet de rechercher le modèle (avec ses paramètres) dans le texte
				#pywikibot.output(u"{ *{ *([%s%s]%s%s) *} *}" % (titre_modele[0].lower(), titre_modele[0].upper(), titre_modele[1:].replace(' ', '[ _]'), unicode(re_params)))
				str_re_titre_modele = "{ *{ *([%s%s]%s%s) *} *}" % (titre_modele[0].lower(), titre_modele[0].upper(), titre_modele[1:].replace(' ', '[ _]+'), str(re_params))

				(timestamp, id) = self.find_add(page, modele)
				date = timestamp.strftime("%B %Y")
				#print "found the add : %s (%i) -> %s" % (timestamp, id, date)
				if date is None:
					pywikibot.output("Error, date is None!")
					return
				#now = datetime.datetime.now()
				#date = now.strftime(u"%B %Y")

				match_modele = re.search(str_re_titre_modele, text)
				if not match_modele:
					pywikibot.output("An error occurred: no match for %s" % str_re_titre_modele)
					return
				#pywikibot.output(match_modele.group(1))
				new = "{{%s|date=%s}}" % (match_modele.group(1), date)
				#pywikibot.output(new)

				text = re.sub(str_re_titre_modele, new, text)
				#text = text.replace(match_modele.group(0), new)
				modeles_modifies_str += "[[Modèle:%(modele)s|{{%(modele)s}}]], " % {'modele':titre_modele}
				count_modeles_modifies += 1

		modeles_modifies_str = modeles_modifies_str[0:-2] # Enlever le ', ' en trop
		if count_modeles_modifies == 1:
			comment = "Bot: Ajout du paramètre 'date' dans le modèle %s" % modeles_modifies_str
		else:
			comment = "Bot: Ajout du paramètre 'date' dans les modèles %s" % modeles_modifies_str

		pywikibot.showDiff(page.get(), text)
		if old_text != page.get():
			pywikibot.output("Page was changed since retrived! Aborting.")
			return
		elif not debug and page.canBeEdited():
			page.put(text, comment = comment)

	def run(self):
		pywikibot.output("Initialisation en cours… date : %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
		t1 = time.time()

		# Génère la liste des pages à traiter
		liste_pages_a_traiter = []
		for titre_cat in self.liste_titres_cats:
			cat = pywikibot.Category(self.site, titre_cat)
			liste_pages_a_traiter.extend([page for page in cat.articles(content=True, namespaces=[0])])

		if not liste_pages_a_traiter:
			pywikibot.output("Aucune page à traiter")
			return

		# Génère la liste complète des modèles utilisables (redirections comprises)
		self.liste_pages_modeles = self.generate_liste_pages_modele(self.titres_modeles_initiaux)

		for modele in self.liste_pages_modeles: pywikibot.output(modele)

		t2 = time.time()
		pywikibot.output("Initialisation terminée. Temps mis : %i secondes" % int(t2-t1))

		if debug:
			liste_pages_a_traiter = [pywikibot.Page(self.site, 'Utilisateur:Toto Azéro/Bac à sable 5')]

		# Analyse page par page
		for page in liste_pages_a_traiter:
			pywikibot.output(page)
			liste_pages_modeles = [couple[0] for couple in page.templatesWithParams()]

			# Intersection entre les listes self.liste_pages_modeles et liste_pages_modeles
			modeles_recherches_presents = list(set(self.liste_pages_modeles) & set(liste_pages_modeles))

			if modeles_recherches_presents:
				self.operate(page, modeles_recherches_presents)

def main():
	bot = BotPrecisionModele()
	bot.run()

if __name__ == "__main__":
	locale.setlocale(locale.LC_ALL, 'fr_FR.utf8')

	global debug
	debug = False

	try:
		main()
	except Exception as myexception:
		#print u'%s %s'% (type(myexception), myexception.args)
		if not debug:
			_errorhandler.handle(myexception)
		raise
	finally:
		pywikibot.stopme()
