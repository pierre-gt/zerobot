#!/usr/bin/python
# -*- coding: utf-8  -*-

"""
Avertissement des demandeurs de la réponse des admins sur leur DRP.

Dernières modifications :
* 1921 : bugfix unicode
* 1920 : bugfix #13 vérifie que le message n'a pas déjà été posté
* 1915 : prise en compte des pages de discussion utilisant Flow
* 1910 : prise en compte du paramètre "sanssuite"
* 1905 : make regex non-greedy
* 1901 : il manquait un "not"
* 1900 : amélioration pour le gestion du cas d'une PàS technique
         (notamment pour les espaces de nom différents du main)
* 1890 : meilleure gestion des IPv6
* 1875 : correction bug section principale vide
* 1874 : correction mineure, introduction whitelist
* 1871 : nouveau statut géré : autre/autreavis
* 1869+ : mise à niveau eqiad
* 1869 : correction encodage date_debut_PaS
* 1865 : suppression ajout "CEST" automatique
		 + correction signature du message 'oui'
* 1864 : gère les modèle où les titres des paramètres ne sont pas renseignés
* 1852 : gère les PàS techniques renommées
* 1834 : gère les PàS techniques où l'en-tête n'est pas formaté normalement
		 + suppression d'une configuration de locale inutile
* 1755 : version adaptée aux Labs
"""

#
# (C) Toto Azéro, 2011-2017
# (C) Framawiki, 2018
#
# Distribué sous licence GNU GPLv3
# Distributed under the terms of the GNU GPLv3 license
# http://www.gnu.org/licenses/gpl.html
#
__version__ = '1921'
__date__ = '2018-10-31 21:21:39 (CET)'
#

import pywikibot
#from pywikibot import flow
import _errorhandler, complements
from pywikibot import config, page, textlib
import locale, re, urllib.request, urllib.parse, urllib.error
from datetime import datetime
import json

class WarnBot:
	def __init__(self):
		self.site = pywikibot.Site('fr', 'wikipedia')
		self.main_page = pywikibot.Page(self.site, "Wikipédia:Demande de restauration de page")
		self.statut_drp_page = pywikibot.Page(self.site, 'Utilisateur:NaggoBot/Statut DRP')

		self.statut_avant = json.loads(self.statut_drp_page.text)
		self.statut_apres = {}

		self.status_knonw = ['non', 'oui', 'attente', 'autreavis', 'autre', 'sanssuite']

		self.messages = {
		# Les messages 'non' et 'oui' ont trois paramètres qui doivent être précisés :
		# 'titre_page', 'lien_drp' et 'date_debut_lien_valide'
		'non': """Bonjour,\n
Ceci est un message automatique vous avertissant que votre demande de restauration pour [[%(titre_page)s]] a été refusée. Afin d'en voir les détails, [[%(lien_drp)s|cliquez ici]]. Ce lien restera actif durant une semaine à compter du %(date_debut_lien_valide)s.""",
		'oui': """Bonjour,\n
Ceci est un message automatique vous avertissant que votre demande de restauration pour [[%(titre_page)s]] a été acceptée. Afin d'en voir les détails, [[%(lien_drp)s|cliquez ici]]. Ce lien restera actif durant une semaine à compter du %(date_debut_lien_valide)s.\n
L'article est à nouveau en ligne, nous vous laissons le soin d'y apporter toutes les preuves nécessaires permettant de conforter son admissibilité.""",

		# Le message 'attente' a deux paramètres qui doivent être précisés :
		# 'titre_page', 'lien_drp'
		'attente': """Bonjour,\n
Ceci est un message automatique vous avertissant que votre demande de restauration pour [[%(titre_page)s]] est en attente d'informations supplémentaires de votre part. Afin d'y apporter tous les arguments et preuves nécessaires, [[%(lien_drp)s|cliquez ici]].""",

		# Le message 'autreavis'/'autre' a deux paramètres qui doivent être précisés :
		# 'titre_page', 'lien_drp'
		'autreavis': """Bonjour,\n
Ceci est un message automatique vous avertissant que votre demande de restauration pour [[%(titre_page)s]] est en cours d'examen. Afin d'en voir les détails, [[%(lien_drp)s|cliquez ici]].""",
		'autre': """Bonjour,\n
Ceci est un message automatique vous avertissant que votre demande de restauration pour [[%(titre_page)s]] est en cours d'examen. Afin d'en voir les détails, [[%(lien_drp)s|cliquez ici]].""",

		# Le message 'oui_PaS' a cinq paramètres qui doivent être précisés :
		# 'titre_page', 'lien_drp', 'date_debut_lien_valide', 'titre_PaS' et 'date_debut_PaS'
		'oui_PaS': """Bonjour,\n
Ceci est un message automatique vous avertissant que votre demande de restauration pour [[%(titre_page)s]] a été acceptée. Afin d'en voir les détails, [[%(lien_drp)s|cliquez ici]]. Ce lien restera actif durant une semaine à compter du %(date_debut_lien_valide)s.\n
L'article est à nouveau en ligne, tout en étant soumis à une procédure communautaire de suppression, afin de savoir si votre article est, ou non, admissible.\n
Vous pouvez accéder à cette page en [[%(titre_PaS)s|cliquant ici]]. Cette procédure dure une semaine à compter du %(date_debut_PaS)s ; nous vous laissons le soin d'y apporter toutes les preuves nécessaires permettant de conforter son admissibilité.""",

		# Le message 'oui_PaS_mais_introuvable' a trois paramètres qui doivent être précisés :
		# 'titre_page', 'lien_drp', 'date_debut_lien_valide'
		'oui_PaS_mais_introuvable': """Bonjour,\n
Ceci est un message automatique vous avertissant que votre demande de restauration pour [[%(titre_page)s]] a été acceptée.
L'article est à nouveau en ligne, tout en étant soumis à une procédure communautaire de suppression, afin de savoir si votre article est, ou non, admissible. Pour plus de détails, [[%(lien_drp)s|cliquez ici]]. Ce lien restera actif durant une semaine à compter du %(date_debut_lien_valide)s.\n
Cette procédure dure une semaine ; nous vous laissons le soin d'y apporter toutes les preuves nécessaires permettant de conforter son admissibilité.""",

		# Le message 'sanssuite' a trois paramètres qui doivent être précisés :
		# 'titre_page', 'lien_drp', 'date_debut_lien_valide'
		'sanssuite': """Bonjour,\n
Ceci est un message automatique vous avertissant que votre demande de restauration pour [[%(titre_page)s]] a été classée sans suite.
Afin d'en voir les détails, [[%(lien_drp)s|cliquez ici]]. Ce lien restera actif durant une semaine à compter du %(date_debut_lien_valide)s.""",
		}

		self.titre_message = "Concernant votre demande de restauration de la page [[%(titre_page)s]]"
		self.resume = "/* Concernant votre demande de restauration de la page [[%(titre_page)s]] */ nouvelle section"
		self.match_titre_requete = re.compile("== *([^=].*?) *==")

		self.whitelist_page = pywikibot.Page(self.site, 'Utilisateur:NaggoBot/Whitelist')
		self.whitelist = [] # list of pywikibot.User
		self.get_whitelist()

	def get_whitelist(self):
		text = self.whitelist_page.get()
		pattern = re.compile("\* \[\[user:(.+)\|.*")
		while pattern.search(text):
			user = pywikibot.User(self.site, pattern.search(text).group(1))
			self.whitelist.append(user)
			text = text.replace(pattern.search(text).group(0), "")

	def analyse_une_section(self, page, match_debut):
		# TODO : - gérer ou du moins éviter les problèmes en cas de doublons de titres.

		text = page.get()

		# Permet de ne garder que le texte contenant les requêtes à étudier,
		# car plusieurs sections se trouvent sur la même page.
		if match_debut == 'Requêtes en cours d\'examen':
			text = text[0:text.index("= Requêtes à traiter =")]
		elif match_debut == 'Requêtes à traiter':
			text = text[text.index("= Requêtes à traiter ="):]

		titres = complements.extract_titles(text, beginning = None, match_title = self.match_titre_requete)
		sections = complements.extract_sections(text, titres)

		return {
		'titres': titres,
		'sections': sections
		}

	def traitement(self):
		pageTraitees = pywikibot.Page(self.site, "Wikipédia:Demande de restauration de page/Traitées")
		pageRefusees = pywikibot.Page(self.site, "Wikipédia:Demande de restauration de page/Refusées")
		pageSanssuite = pywikibot.Page(self.site, "Wikipédia:Demande de restauration de page/Sans suite")
		liste_sections = [(self.main_page, 'Requêtes à traiter'), (self.main_page, "Requêtes en cours d'examen"), (pageTraitees, None), (pageRefusees, None), (pageSanssuite, None)]

		for couple in liste_sections:
			dict = self.analyse_une_section(page = couple[0], match_debut = couple[1])
			sections = dict['sections']

			if not sections:
				continue

			for numero_section in sections:
				pywikibot.output('\n')
				titre_section = dict['titres'][numero_section]
				section = sections[numero_section]
				templates = textlib.extract_templates_and_params(section)
				# templates est du type :
				#     [(u'DRP début', {u'date': u'27 février 2010 à 14:56 (CEC)'
				#     , u'statut': u'oui'}), (u'DRP fin', {})]

				PaS = False
				found_full_template = False
				for template in templates:
					if template[0] == 'DRP début':
						if not ('statut' in template[1]):
							pywikibot.output("pas de paramètre 'statut' trouvé")
							continue
						elif not ('date' in template[1]):
							pywikibot.output("pas de paramètre 'date' trouvé")
							continue

						found_full_template = True
						statut_actuel = template[1]['statut']
						date = template[1]['date']
						if 'PàS' in template[1]:
							pywikibot.output('phase try 0')
							pywikibot.output(template[1]['PàS'])
							if template[1]['PàS'] == 'oui':
								pywikibot.output('phase try 1')
								PaS = True
								page_PaS = None
							elif template[1]['PàS'] != '':
								pywikibot.output('phase try 2')
								PaS = True
								page_PaS = pywikibot.Page(self.site, "%s/Admissibilité" % template[1]['PàS']).toggleTalkPage()

				pywikibot.output('found_full_template = %s' % found_full_template)

				if not found_full_template:
					pywikibot.output('Fully fulfilled template was not found, skipping to next section.')
					continue

				pywikibot.output("PaS = %s" % PaS)
				if PaS:
					try:
						pywikibot.output("page_PaS = %s" % page_PaS)
					except:
						pywikibot.output("no page_PaS")

				# Pour enlever les == et les éventuels espaces
				# du titre de la section puis les [[…]] qui sont
				# supprimés de l'URL par MediaWiki.
				titre_section = titre_section[2:-2]
				titre_section = titre_section.strip()

				titre_section_SQL = titre_section

				titre_section_MediaWiki = titre_section
				titre_section_MediaWiki = titre_section_MediaWiki.replace("[[", "")
				titre_section_MediaWiki = titre_section_MediaWiki.replace("]]", "")


				pywikibot.output("=== %s ===" % titre_section)
				pywikibot.output("statut_actuel = %s" % statut_actuel)
				pywikibot.output("date = %s" % date)


				if statut_actuel not in self.status_knonw:
					# Si le demande de restauration ne possède pas un de ces statuts,
					# il est inutile d'aller plus loin car seuls ceux-ci nécessitent
					# de laisser un message au demandeur.
					continue

				# Vérifier si la requête a déjà été analysée par le bot.
				if titre_section_SQL in self.statut_avant:
					# Si oui, et si le statut est toujours le même, il n'y a rien à faire
					statut_traite = self.statut_avant[titre_section_SQL]

					pywikibot.output(statut_traite)

					# La vérification d'un éventuel lancement d'une PàS technique
					# pour la restauration n'est faite que par la suite, le statut
					# 'oui_PaS' ne peut donc pas encore être le statut_actuel,
					# même si une PàS a été lancée !
					# On remplace donc l'éventuel statut traité 'oui_PaS' par un
					# simple 'oui'.
					if statut_traite == 'oui_PaS':
						statut_traite = 'oui'

					if statut_traite == statut_actuel:
						# Si le statut actuel est le même que celui qui a déjà été
						# traité, il n'y a rien d'autre à faire : le demandeur
						# a déjà été averti.
						pywikibot.output('DRP déjà traitée !')
						self.statut_apres[titre_section_SQL] = statut_actuel
						continue
					else:
						pywikibot.output('DRP déjà traitée mais statut différent…')

				#print section

				# Si on arrive ici, c'est que le demandeur n'a pas été averti du
				# statut actuel
				m1 = re.search("[dD]emandée? par .*\[ *\[ *([uU]tilisateur:|[uU]ser:|[sS]p[eé]cial:[cC]ontributions/)(?P<nom_demandeur>[^|\]]+)(\|| *\] *\])", section)
				m2 = re.search("[dD]emandée? par {{u'?\|(?P<nom_demandeur>[^|]+?)}}", section)
				m3 = re.search("[dD]emandée? par (?P<nom_demandeur>[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", section)

				if m1:
					nom_demandeur = m1.group('nom_demandeur')
					#print 'm1'
				elif m2:
					nom_demandeur = m2.group('nom_demandeur')
					#print 'm2'
				elif m3:
					nom_demandeur = m3.group('nom_demandeur')
					#print 'm3'
				else:
					pywikibot.output('nom du demandeur introuvable !')
					continue

				#print nom_demandeur

				try:
					demandeur = pywikibot.User(self.site, nom_demandeur)
				except Exception as e:
					pywikibot.output('erreur dans la recuperation du demandeur : ' + repr(e))
					continue
				if 'autopatrolled' in demandeur.groups():
					pywikibot.output('demandeur autopatrolled : inutile de laisser un message')
					continue
				elif demandeur in self.whitelist:
					pywikibot.output("l'utilisateur est sur la whitelist")
					continue


				page_discussion_demandeur = demandeur.getUserTalkPage()
				pywikibot.output(page_discussion_demandeur)

				m = re.findall("\[ *\[ *(?P<titre_page>.*?) *\] *\]", titre_section)
				if not m:
					pywikibot.output('Titre de la page concernée introuvable !')
					continue

				titre_page_concernee = m[0] # Si plusieurs titres sont présents, vérifier arbitrairement que le premier
				titre_pages_concernees = ']], [['.join(m)
				pywikibot.output(titre_page_concernee)

				# Vérifier si une PàS technique pour la restauration a été
				# lancée ou non.
				if statut_actuel == 'oui':
					if PaS:
						statut_actuel = 'oui_PaS'
						pywikibot.output('oui_PaS')
						if not page_PaS or not page_PaS.exists():
							try:
								page_PaS = pywikibot.Page(self.site, titre_page_concernee + "/Admissibilité").toggleTalkPage() #pywikibot.Page(self.site, u"Discussion:%s/Suppression" % titre_page_concernee)
								page_PaS.get()
							except:
								pywikibot.output('erreur : la PàS technique ne semble pas exister ou n\'est pas normalisée !')
								statut_actuel = 'oui_PaS_mais_introuvable'
						if page_PaS:
							# La PàS peut avoir été renommée
							if page_PaS.isRedirectPage():
								page_PaS = page_PaS.getRedirectTarget()

							if re.search("[pP]roposé *par.* ([0-9]{1,2}.*20[01][0-9]) à [0-9]{2}:[0-9]{2}", page_PaS.get()):
								date_debut_PaS = re.search("[pP]roposé *par.* ([0-9]{1,2}.*20[01][0-9]) à [0-9]{2}:[0-9]{2}", page_PaS.get()).group(1)
							else:
								# Si la date n'est pas formatée comme attendue sur la PàS, le bot
								# cherche sa date de création en remontant l'historique, puis l'exprime
								# sous la forme attendue.
								date_creation = list(page_PaS.revisions())[-1].timestamp
								date_debut_PaS = date_creation.strftime("%d %B %Y")

				message = self.messages[statut_actuel]

				# La fonction urllib.quote() permet d'encoder une URL.
				# Ici, seul le titre de la section a besoin d'être encodé.
				# Cependant, MediaWiki remplace les espaces par des tirets bas ('_')
				# et les % dans l'encodage par des points ('.').
				lien_drp = "%s#%s" % (self.main_page.title(as_link = False), urllib.parse.quote(titre_section_MediaWiki.encode('utf-8'), safe=" /").replace(" ", "_").replace("%", "."))

				#pywikibot.output(u'lien_drp = %s' % lien_drp)

				if statut_actuel in ['non', 'oui', 'oui_PaS_mais_introuvable', 'sanssuite']:
					message = message % {'titre_page':titre_page_concernee, 'lien_drp':lien_drp, 'date_debut_lien_valide':date}
				elif statut_actuel == 'oui_PaS':
					if not type(date_debut_PaS) == str:
						pywikibot.output("Formattage de date_debut_PaS")
						date_debut_PaS = date_debut_PaS.decode('utf-8')
					message = message % {'titre_page':titre_page_concernee, 'lien_drp':lien_drp, 'date_debut_lien_valide':date, 'titre_PaS':page_PaS.title(as_link = False), 'date_debut_PaS':date_debut_PaS}
				elif statut_actuel in ['attente', 'autre', 'autreavis']:
					message = message % {'titre_page':titre_page_concernee, 'lien_drp':lien_drp}
				else:
					pywikibot.output('statut inconnu : %s' % statut_actuel)
					continue

				#
				# Mauvaise gestion des IPv6 par pywikibot
				# Les caractères doivent être en majuscules
				#
				pattern_ipv6 = "Discussion utilisateur:(([0-9a-zA-Z]{,4}:){7}[0-9a-zA-Z]{,4})"
				if re.search(pattern_ipv6, page_discussion_demandeur.title()):
					ipv6 = re.search(pattern_ipv6, page_discussion_demandeur.title()).group(1)
					ipv6 = ipv6.upper()
					page_discussion_demandeur = pywikibot.Page(pywikibot.Site(), "Discussion utilisateur:"+ipv6)
				#

				while page_discussion_demandeur.isRedirectPage():
					page_discussion_demandeur = page_discussion_demandeur.getRedirectTarget()

				titre = self.titre_message % {'titre_page': titre_pages_concernees}
				#if page_discussion_demandeur.is_flow_page():
				#	board = pywikibot.flow.Board(self.site, page_discussion_demandeur.title())
				#	board.new_topic(titre, message)
				#	# print("flow", page_discussion_demandeur.title(), titre, message)

				#else:
				if page_discussion_demandeur.text:
					page_discussion_demandeur.text += '\n\n'
					if message in page_discussion_demandeur.text:
						pywikibot.output('BUG #13: le message a déjà été posté sur %s !' % page_discussion_demandeur.title(as_link=True))
						continue

				page_discussion_demandeur.text += "== %s ==" % titre + '\n' + message + '\n\nDistribué par [[Utilisateur:NaggoBot|NaggoBot]], le ~~~~~'

				comment = self.resume % {'titre_page': titre_pages_concernees}
				pywikibot.output(comment)
				try:
					page_discussion_demandeur.save(summary=comment, minorEdit=False)
					# print(page_discussion_demandeur.title(),titre,message)
				except:
					pywikibot.output('erreur lors de la publication du message !')
					continue

				# Enregistrer la requête comme analysée par le bot
				self.statut_apres[titre_section_SQL] = statut_actuel
		print(json.dumps(self.statut_apres))
		sorted_dict={k: self.statut_apres[k] for k in sorted(self.statut_apres)}
		self.statut_drp_page.text = json.dumps(sorted_dict, sort_keys=True)
		self.statut_drp_page.save(asynchronous=True, summary="Mise à jour des statuts DRP")

def main():
	locale.setlocale(locale.LC_ALL, 'fr_FR.utf8')
	bot = WarnBot()
	bot.traitement()

if __name__ == '__main__':
    try:
        main()
    except Exception as myexception:
        _errorhandler.handle(myexception)
        raise
    finally:
        pywikibot.stopme()
