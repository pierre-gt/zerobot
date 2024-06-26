#!/usr/bin/python
# -*- coding: utf-8  -*-

"""
Classement et archivage des requêtes aux sysops (génération 3.0).

Ce script classe les requêtes d'une page de requêtes aux sysops.

Différences avec la génération 1.0 :
	- ajout d'un quatrième cas au paramètre status: sanssuite, en plus de rien, oui, non

Dernières corrections :
*
"""

#
# (C) Toto Azéro, 2011-2017
# (C) Framawiki, 2018
#
# Distribué sous licence GNU GPLv3
# Distributed under the terms of the GNU GPLv3 license
# http://www.gnu.org/licenses/gpl.html
#
__version__ = '$Id: sysops_archives_renew.py 3000 2016-01-04 22:52:30 (CET) Framawiki $'
__date__ = '2016-01-04 22:52:30 (CET)'
#

import _errorhandler
import pywikibot
from pywikibot import config, page, textlib
import locale, re
from datetime import datetime
import complements

class PutQueue:
	def __init__(self):
		self.queue = []

	def add(self, page, text, comment):
		self.queue.append((page, text, comment))

	def safe_put(self, page, text, comment):
		try:
			page.put(text, summary = comment)
		except pywikibot.SpamblacklistError as errorBlacklist:
			for url in errorBlacklist.url.split(', '):
				text.replace(url, "<nowiki>%s</nowiki>" % url)
			self.site.unlock_page(page) # Strange bug, page locked after the error
			page.put(text, summary = comment)

	def put_all(self):
		total_put = 0
		try:
			while self.queue:
				page, text, comment = self.queue.pop(0)
				self.safe_put(page, text, comment)
				total_put += 1

		except Exception as myexception:
			#e = sys.exc_info()
			#pywikibot.output(e)

			if total_put == 0:
				_errorhandler.message("WARNING: Nothing was put, and nothing will be")
				raise myexception
			else:
				_errorhandler.message("CRITICAL: Some things were put, you may have to undo changes!", addtags={'page': page.title(as_link=True)})
				raise myexception


class TreatementBot:
	def __init__(self, raccourci):
		"""
		Initiation du bot.

		Définition (entre autres) :
			- du dictionnaire principal (self.dict) contenant :
				* les délai de classement, d'archivage et de suppression des requêtes
				* la méthode d'« archivage » à employer (archivage classique ou suppression)
			- de la page principale des requêtes (self.main_page)
			- de l'éventuelle page d'archivage des requêtes acceptées (self.accepted_page)
			- de l'éventuelle page d'archivage des requêtes refusées (self.refused_page)

		TODO:
			- utiliser le paramètre 'raccourci' supportée par la fonction pour
			  prédéfinir la définition de chaque variable précédemment citée pour
			  l'ensemble des pages de requêtes aux admins traitées (RA, DR, DPP, DRP, DIPP)

		WARNING : self.accepted_page doit être différent de self.refused_page
		TODO: corriger l'implémentation pour que ce ne soit pas le cas
		"""

		self.site = pywikibot.Site('fr', 'wikipedia')

		###
		# Définitions particulières à la page de requêtes
		###
		if raccourci == 'drp':
			self.dict = {
			'archiver': {'acceptees': True, 'refusees': True, 'sanssuite': True},
			'supprimer': {'acceptees': False, 'refusees': False, 'sanssuite': False},
			'delai': {'classement': 24, 'archivage': 7*24, 'suppression': 7*24} # En heures,
			}

			self.main_page = pywikibot.Page(self.site, "Wikipédia:Demande de restauration de page")
			self.accepted_page = pywikibot.Page(self.site, "Wikipédia:Demande de restauration de page/Traitées")
			self.refused_page = pywikibot.Page(self.site, "Wikipédia:Demande de restauration de page/Refusées")
			self.sanssuite_page = pywikibot.Page(self.site, "Wikipédia:Demande de restauration de page/Sans suite")

			self.text_below_waiting_requests = "\n{{Wikipédia:Requête aux administrateurs/Note:Requêtes en cours}}\n<!-- DEBUT DES REQUÊTES EN COURS =============================================================== -->"
			self.text_below_untreated_requests = "\n{{Wikipédia:Requête aux administrateurs/Note:Requêtes à traiter}}\n<!-- DEBUT DES REQUÊTES A TRAITER ========================================== -->"
			self.template_prefix = "DRP"
			self.template_title = "%s début" % self.template_prefix
			self.template_end_title = "%s fin" % self.template_prefix
			self.archivePrefix = "Archives"
		###

		self.les_mois = {
		"janvier": "01",
		"février": "02",
		"mars": "03",
		"avril": "04",
		"mai": "05",
		"juin": "06",
		"juillet": "07",
		"août": "08",
		"septembre": "09",
		"octobre": "10",
		"novembre": "11",
		"décembre": "12"
		}

		self.match_date = re.compile("(?P<day>[0-9]+) *(?P<month>[^ ]+) *(?P<year>20[0-9]{2}) *à *(?P<hours>[0-9]{2})[h:](?P<minutes>[0-9]{2})")
		self.match_titre_requete = re.compile("(\n|^)== *([^=].+[^=]) *==")

	def analyse_section(self, section, template_title = None):
		"""
		Analyse une section et retourne un dictionnaire contenant la date et le statut
		de la section (retourne : {'date': (string), 'statut': (string)}).
		Par défaut, le titre du modèle à analyser est celui du modèle correspondant
		à la page de requête associée à la classe (self.template_title).
		"""
		if not template_title:
			template_title = self.template_title

		date = None
		statut = None
		templates = textlib.extract_templates_and_params(section)
		# templates est du type :
		#	 [(u'RA début', {u'date': u'27 février 2011 à 14:56 (CET)'
		#	 , u'statut': u'oui'}), (u'RA fin', {})]
		# avec éventuellement d'autres modèles, utilisés dans la requête par
		# les contributeurs, et se trouvant entre le {{RA début}} et le {{RA fin}}

		for template in templates:
		# Si le modèle est celui qui annonce le début de la section.
			if template[0] == template_title: #modifié (todo A-1)
			# On extrait les paramètres utiles (statut et date)
				try:
					statut = template[1]['statut']
					date = template[1]['date']
				except:
					pywikibot.output("Erreur ! Les paramètres 'statut' et 'date' ne semblent pas exister !")
					return None
				# On arrête d'analyser les modèles, étant donné qu'on a trouvé
				# celui qui nous intéresse.
				break

		return {'date': date, 'statut': statut}

	def classement(self):
		"""
		Classement des requêtes.
		Le bot prend en compte trois statuts, passés par le paramètre 'statut'
		dans le modèle {{RA début}} :
			- 'oui' : la requête a été acceptée
			- 'non' : la requête a été refusée
			- 'attente' : la requête est en attente
			- 'sanssuite' : la requête est close et n'a donnée aucune suite

		Si le paramètre statut n'est pas renseigné, où s'il ne correspond à aucun des
		trois statuts connus par le bot, celui-ci ignore la requête, et la laisse où
		elle est.

		Les requêtes sont classées dès leur que la date, renseignée avec le
		paramètre 'date' du modèle {{RA début}}, satisfait le délai configuré
		dans le dictionnaire principal self.dict :
			self.dict['delai']['classement'] (en heures)

		Les requêtes possédant un statut et satisfaisant le délai configuré
		sont supprimées de la section "= Requêtes à traiter =" et sont envoyées :
			- sur la page self.accepted_page pour les requêtes acceptées
				(page définie dans la fonction __init__)
			- sur la page self.refused_page pour les requêtes refusées
				(page définie dans la fonction __init__)
			- dans la section "= Requêtes en attente =" pour les requêtes en attente

		Les requêtes précédemment en attente et n'ayant pas changé de statut depuis
		sont laissées dans l'ordre initial dans la section "= Requêtes en attente =".

		Aucun paramètre n'est supporté pour cette fonction.
		"""
		self.text = self.main_page.get()
		self.text = self.text.replace(self.text_below_waiting_requests, '')
		self.text = self.text.replace(self.text_below_untreated_requests, '')

		#print self.text_below_waiting_requests
		#print self.text_below_untreated_requests
		#print self.text
		#print re.search(re.compile(u"= *Requêtes en cours d'examen *= *\n+(.*)\n*= *Requêtes à traiter *=", re.S), self.text)

		text_requetes_en_attente = re.search(re.compile("= *Requêtes en cours d'examen *= *\n+(.*)\n*= *Requêtes à traiter *=", re.S), self.text).group(1)
		#pywikibot.output('text_requetes_en_attente')
		#pywikibot.output(text_requetes_en_attente)
		#
		#pywikibot.output('--------------------------------')

		self.text = self.text.replace(text_requetes_en_attente, '')
		self.text = re.sub("(= Requêtes à traiter =\n*)\n", "\\1\n%s" % text_requetes_en_attente.replace('\\', '{[(+-/antislash/-+)]}'), self.text)
		self.text = self.text.replace("{[(+-/antislash/-+)]}", '\\')

		text_requetes_a_traiter = re.search("= *Requêtes à traiter *=", self.text).group(0)

		titres = complements.extract_titles(self.text, beginning = text_requetes_a_traiter, match_title = self.match_titre_requete)
		sections = complements.extract_sections(self.text, titres)

		self.text = re.sub("(= *Requêtes en cours d'examen *= *)", "\\1%s" % self.text_below_waiting_requests, self.text)
		self.text = re.sub("(= *Requêtes à traiter *= *)", "\\1%s" % self.text_below_untreated_requests, self.text)

		#pywikibot.output(self.text)

		#for numero_section in sections:
		#	print '--------------------------------'
		#	print sections[numero_section]

		# Dictionnaire de classement des requêtes en fonction de
		# leur statut
		dict_requetes_par_statut = {
		'oui': list(),
		'non': list(),
		'attente': list(),
		'sanssuite': list(),
		'': list() # requêtes sans statut ou ne répondant pas à la contrainte du délai
		}

		if not sections:
			sections = []

		for numero_section in sections:
			pywikibot.output('--------------------------------')
			pywikibot.output(titres[numero_section])

			analyse = self.analyse_section(sections[numero_section])
			if analyse == None: # Une erreur a eu lieu
				continue
			date = analyse['date']
			statut = analyse['statut']

			pywikibot.output('date found: %s' % date)
			pywikibot.output('statut found: %s' % statut)

			if statut not in ['oui', 'non', 'attente', 'autreavis', 'autre', 'sanssuite']:
				# Le statut de la requête n'est pas reconnu ou pas pris en charge
				continue

			if not date and statut not in ['attente', 'autreavis', 'autre']:
				# Si la requête n'a pas de date et n'est pas en attente,
				# on la laisse  l'endroit où elle est, pour éviter de
				# modifier l'ordre d'apparition des requêtes.
				pywikibot.output('aucune date renseignée')
				continue

			if statut in ['attente', 'autreavis', 'autre']:
				# Si la requête est en attente, on la classe dans le dictionnaire,
				# on la supprime du texte mais il est inutile d'aller plus loin
				# pour analyser la date, puisqu'elle sera automatiquement classée
				# dans la section "Requêtes en cours d'examen"
				pywikibot.output('Status found: wainting')
				self.text = self.text.replace(sections[numero_section], '')
				dict_requetes_par_statut['attente'].append(sections[numero_section])
				continue

			try:
				date = self.match_date.search(date)
				#pywikibot.output(date.group('month'))

				# Il est préférable de reformater la date, toujours au format string
				# avant de la parser avec la commande datetime.strptime.
				# Ici, la date est normalisée suivant le format suivant :
				#		jour mois année heures:minutes (tout en chiffres)
				# ex :	13 02 2012 23:34
				# On préfèrera utiliser exclusivement des chiffres pour éviter
				# des problèmes liés aux accents sur le nom de certains mois,
				# tels février, décembre et août.
				text_date = "%s %s %s %s:%s" % (date.group('day'), self.les_mois[date.group('month')], date.group('year'), date.group('hours'), date.group('minutes'))
				date = datetime.strptime(text_date, "%d %m %Y %H:%M")
				pywikibot.output("date is %s" % date)
			except:
				pywikibot.output('erreur: problème avec la date')
				continue

			now = datetime.now()

			#pywikibot.output(now)
			#pywikibot.output(self.dict['delai']['classement'])
			pywikibot.output("from then to now: %s, that is %i hours" % ((now-date), ((now-date).seconds/3600) + (now-date).days*24))

			# Si la requête possède le délai requis pour être classée…
			if self.dict['delai']['classement'] <= ((now-date).seconds/3600 + (now-date).days*24):
				pywikibot.output('=> classement')

				# …on place la requête dans la liste appropriée…
				dict_requetes_par_statut[statut].append(sections[numero_section])

				# On supprime la requête de la section des requêtes à traiter.
				self.text = self.text.replace(sections[numero_section], '')

			else: # …sinon, on la laisse en place
				pywikibot.output('=> pas de classement')
				if sections[numero_section] in text_requetes_en_attente:
					self.text = self.text.replace(sections[numero_section], '')
					dict_requetes_par_statut['attente'].append(sections[numero_section])
				else:
					dict_requetes_par_statut[''].append(sections[numero_section])

		##
		# Pour les tests
		##
		#for statut in dict_requetes_par_statut:
		#	pywikibot.output('=================================')
		#	pywikibot.output(statut)
		#	for requete in dict_requetes_par_statut[statut]:
		#		pywikibot.output('--------------------------------')
		#		pywikibot.output(requete)
		#
		#pywikibot.output('=================================')
		##

		# Récupération des requêtes déjà acceptées/refusées
		# et création des textes adéquats pour chaque type de
		# requêtes.
		text_accepted = self.accepted_page.get()
		if text_accepted:
			while text_accepted[-2:] != '\n\n': # Pour rajouter des sauts de lignes si nécessaire.
				text_accepted += '\n'
		for requete in dict_requetes_par_statut['oui']:
			text_accepted += requete

		text_refused = self.refused_page.get()
		if text_refused:
			while text_refused[-2:] != '\n\n':
				text_refused += '\n'
		for requete in dict_requetes_par_statut['non']:
			text_refused += requete

		text_sanssuite = self.sanssuite_page.get()
		if text_sanssuite:
			while text_sanssuite[-2:] != '\n\n':
				text_sanssuite += '\n'
		for requete in dict_requetes_par_statut['sanssuite']:
			text_sanssuite += requete

		text_waiting = ""
		for requete in dict_requetes_par_statut['attente']:
			text_waiting += requete

		#pywikibot.output('text_waiting')
		#pywikibot.output(text_waiting)

	#	text_untreated = ""
	#	for requete in dict_requetes_par_statut['']:
	#		text_untreated += requete
	#
	#	if text_untreated:
	#		while self.text[-2:] != '\n\n': # Pour rajouter des sauts de lignes si nécessaire.
	#			self.text += '\n'
	#
	#	self.text += text_untreated


		if text_waiting:
			# Permet d'avoir deux sauts de lignes après la dernière section,
			# en fin de page
			text_waiting = re.sub("(\n)*$", "\n\n", text_waiting)


		# Mise à jour
		self.text = re.sub("\n+(= *[rR]equêtes *à *traiter *= *)", "\n%s\\1" % text_waiting.replace('\\', '{[(+-/antislash/-+)]}'), self.text)
		self.text = self.text.replace("{[(+-/antislash/-+)]}", '\\')

		comment = "Classement des requêtes (%i requête(s) acceptée(s), %i requête(s) refusée(s), %i requête(s) en attente, %i requête(s) classées sans suite)" % (len(dict_requetes_par_statut['oui']), len(dict_requetes_par_statut['non']), len(dict_requetes_par_statut['attente']), len(dict_requetes_par_statut['sanssuite']))
		#pywikibot.output(self.text)
		#pywikibot.showDiff(self.main_page.get(), self.text)
		self.put_queue.add(self.main_page, self.text, comment = comment)
		pywikibot.output(comment)

		comment = "Classement des requêtes : %i requête(s) acceptée(s)" % len(dict_requetes_par_statut['oui'])
		self.put_queue.add(self.accepted_page, text_accepted, comment = comment)
		pywikibot.output(comment)

		comment = "Classement des requêtes : %i requête(s) refusée(s)" % len(dict_requetes_par_statut['non'])
		self.put_queue.add(self.refused_page, text_refused, comment = comment)
		pywikibot.output(comment)

		comment = "Classement des requêtes : %i requête(s) sans suite" % len(dict_requetes_par_statut['sanssuite'])
		self.put_queue.add(self.sanssuite_page, text_sanssuite, comment = comment)
		pywikibot.output(comment)

	def archivage(self):
		"""
		Archivage ou suppression des requêtes classées (suivant le paramétrage du
		dictionnaire principal self.dict), dès lors qu'elles satisfaisent le délai
		configuré (self.dict['delai']['archivage'] et self.dict['delai']['suppression']).

		Les requêtes archivées sont transférée vers une sous-page de la page principale
		(self.main_page), en rajoutant le suffixe '/Archives%i' avec %i un integer.
		Le bot détecte automatiquement la page d'archives en cours, et crée une nouvelle
		page dès que le nombre de 250 sections est atteint.

		TODO (D):
			- mettre à jour la page principale d'archives lorsqu'une nouvelle page
			  d'archives est créée.
			- vérifier l.475 (new_text = archive_page.get() + '\\n' + text_to_archive)
		"""
		to_do = ['acceptees', 'refusees', 'sanssuite']
		for type in to_do:
			if type == 'acceptees':
				page_en_cours = self.accepted_page
				#text = self.accepted_page.get()
			elif type == 'refusees':
				page_en_cours = self.refused_page
				#text = self.refused_page.get()
			elif type == 'sanssuite':
				page_en_cours = self.sanssuite_page
				#text = self.refused_page.get()
			pywikibot.output(page_en_cours)

			text = page_en_cours.get()
			if not text:
				pywikibot.output("Aucun texte dans la page !")
				continue

			titres = complements.extract_titles(text, beginning = "", match_title = self.match_titre_requete)
			sections = complements.extract_sections(text, titres)

			text_to_archive = ""
			requests_to_archive = []
			requests_to_delete = []

			if not sections:
				sections = []

			# Début de la boucle d'analyse de chacune des sections, au cas par cas.
			for numero_section in sections:
				pywikibot.output('--------------------------------')
				pywikibot.output(titres[numero_section])

				analyse = self.analyse_section(sections[numero_section])
				if analyse == None: # Une erreur a eu lieu
					continue
				date = analyse['date']
				statut = analyse['statut']

				if not date:
					pywikibot.output('erreur : pas de date !')
					continue

				try:
					date = self.match_date.search(date)
					pywikibot.output(date.group('month'))

					# Il est préférable de reformater la date, toujours au format string
					# avant de la parser avec la commande datetime.strptime.
					# Ici, la date est normalisée suivant le format suivant :
					#		jour mois année heures:minutes (tout en chiffres)
					# ex :	13 02 2012 23:34
					# On préfèrera utiliser exclusivement des chiffres pour éviter
					# des problèmes liés aux accents sur le nom de certains mois,
					# tels février, décembre et août.
					text_date = "%s %s %s %s:%s" % (date.group('day'), self.les_mois[date.group('month')], date.group('year'), date.group('hours'), date.group('minutes'))
					date = datetime.strptime(text_date, "%d %m %Y %H:%M")
					pywikibot.output("date is: %s" % date)
				except:
					pywikibot.output('erreur: problème avec la date')
					continue

				now = datetime.now()

				#pywikibot.output(now)
				pywikibot.output("délai classement : %i heures" % self.dict['delai']['classement'])
				#pywikibot.output((now-date))
				pywikibot.output("from then to now: %s, that is %i hours" % ((now-date), ((now-date).seconds/3600) + (now-date).days*24))

				if self.dict['archiver'][type]:
				# Si l'archivage des requêtes est activé.
					if self.dict['delai']['archivage'] <= ((now-date).seconds/3600 + (now-date).days*24):
						pywikibot.output('=> archivage')
						text_to_archive += sections[numero_section]
						requests_to_archive.append(sections[numero_section])
						text = text.replace(sections[numero_section], '')
					else:
						pywikibot.output('=> pas d\'archivage')

				elif self.dict['supprimer'][type]:
				# Sinon, si leur suppression est activée.
					if self.dict['delai']['suppression'] <= ((now-date).seconds/3600 + (now-date).days*24):
						pywikibot.output('=> suppression')
						text = text.replace(sections[numero_section], '')
						requests_to_delete.append(sections[numero_section])
					else:
						pywikibot.output('=> pas de suppression')

			# Fin de la boucle traitant les sections au cas par cas.
			#
			# La variable text_to_archive contient désormais la totalité des requêtes
			# à archiver (texte), si l'archivage est activé pour le type de requêtes en
			# cours de traitement.
			#
			# La variable requests_to_archive contient désormais la liste des requêtes
			# à archiver, si l'archivage est activé pour le type de requêtes en
			# cours de traitement.


			if self.dict['archiver'][type]:
				if not text_to_archive:
					# Si rien n'est à archiver, on passe directement
					# au traitement suivant (de l'autre type de requêtes).
					continue

				# Trouver le numéro de la page d'archive en cours
				archiveNumber=1
				archive_page = None
				while True:
					previous_archive_page = archive_page
					archive_page = pywikibot.Page(self.site, self.main_page.title(as_link = False) + "/%s%i" % (self.archivePrefix, archiveNumber))
					if not archive_page.exists():
						break
					archiveNumber += 1

				if previous_archive_page != None:
					archiveNumber -= 1
					archive_page = previous_archive_page

				pywikibot.output(archive_page)
				#pywikibot.output(text_to_archive)

				# La variable archiveNumber contient à présent le numéro
				# de la page d'archive en cours.

				# Si la page d'archive existe (si elle n'existe pas, c'est qu'aucune page
				# d'archive n'a été trouvée par le bot.
				if archive_page.exists():

					# On compte le nombre de requêtes déjà présentes dans
					# la page d'archive en cours.
					# Pour cela, on remplace chaque titre de section par '{[$REQUETE$]}'
					# et on compte le nombre de '{[$REQUETE$]}'.
					nombre_de_sections = re.sub(self.match_titre_requete, '{[$REQUETE$]}', archive_page.get()).count('{[$REQUETE$]}')

					#print re.sub(self.match_titre_requete, '{[$REQUETE$]}', text)
					pywikibot.output('nombre_de_sections = %i' % nombre_de_sections)

					if nombre_de_sections > 250:
						old_archiveNumber = archiveNumber
						old_archive_page = archive_page

						# On récupère la dernière requête pour donner la dernière date
						# de la page d'archive.
						text_temp = old_archive_page.get()
						old_archives = complements.extract_sections(text_temp, complements.extract_titles(text_temp, "", self.match_titre_requete))
						last_archive = old_archives[len(old_archives) - 1]

						templates = textlib.extract_templates_and_params(last_archive)


						for template in templates:
							pywikibot.output(template)
							if template[0] == self.template_title:#u'RA début': #modifié (todo A-1)
								statut = template[1]['statut']
								date = template[1]['date']
								pywikibot.output(date)

								# On arrête d'analyser les modèles, étant donné qu'on a trouvé
								# celui qui nous intéresse.
								break


						if date:
							try:
								pywikibot.output(date)
								last_date = self.match_date.search(date)
								pywikibot.output(last_date)
								last_date = "%s %s %s" % (last_date.group('day'), last_date.group('month'), last_date.group('year'))
								pywikibot.output(last_date)
							except Exception as myexception:
								pywikibot.output('%s %s' % (type(myexception), myexception.args))
								pywikibot.output('erreur: problème avec la date')
						else:
							pywikibot.output('erreur : pas de date !')

						# La variable last_date contient désormais la date de la dernière
						# requête de la page d'archives.

						archiveNumber += 1
						archive_page = pywikibot.Page(self.site, self.main_page.title(as_link = False) + "/%s%i" % (self.archivePrefix, archiveNumber))
						new_text = text_to_archive
						pywikibot.output("Plus de 250 requêtes archivées -> création d'une nouvelle page d'archive (n°%i)" % archiveNumber)

						# Mise à jour de la page d'archives principale
						main_archive_page = pywikibot.Page(self.site, self.main_page.title() + "/Archives")
						text_temp = main_archive_page.get()
						text_temp = re.sub("(\# *\[\[%s\]\]) *" % old_archive_page.title(as_link = False), "\\1 (jusqu'au %s)\n# %s" % (last_date, archive_page.title(as_link = True)), text_temp)
						self.put_queue.add(main_archive_page, text_temp, comment = "Création d'une nouvelle page d'archives")

					else:
						pywikibot.output("Moins de 250 requêtes archivées -> page d'archive actuelle (n°%i)" % archiveNumber)
						new_text = archive_page.get()
						while new_text[-2:] != '\n\n': # Pour rajouter des sauts de lignes si nécessaire.
							new_text += '\n'
						new_text += text_to_archive

				else: # Aucune page d'archive n'a été trouvée par le bot.
					pywikibot.output("1ère page d'archive ! Aucune ne semble exister actuellement…")
					new_text = text_to_archive

				# Mise à jour de la page de classement en cours de traitement
				# ainsi que de la apge d'archive
				comment = ("Archivage de %i requêtes" % len(requests_to_archive))
				try:
					pywikibot.output('******************************************************')
					self.put_queue.add(page_en_cours, text, comment = (comment + " vers %s" % archive_page.title(as_link = True)))
					self.put_queue.add(archive_page, new_text, comment = comment)

					# do it now, otherwise conflicts (eg. if accepted and refused
					# go to the same place, the second update will override the
					# first one, see https://fr.wikipedia.org/w/index.php?diff=133677130&diffonly=1)
					self.put_queue.put_all()
				except Exception as myexception:
					pywikibot.output("erreur type 2")
					#print u'%s %s' % (type(myexception), myexception.args)


			elif self.dict['supprimer'][type]:
				comment = ("Suppression de %i requêtes" % len(requests_to_delete))
				self.put_queue.add(page_en_cours, text, comment = comment)

	def traitement(self):
		"""
		Traitement complet des requêtes aux admins :
			- classement
			- archivage
		"""
		self.put_queue = PutQueue()
		self.classement()
		self.put_queue.put_all()
		self.archivage()
		self.put_queue.put_all()


def main():
	# Configuration de locale
	try:
		locale.setlocale(locale.LC_ALL, 'fr_FR.utf8')
	except:
		locale.setlocale(locale.LC_ALL, 'fr_FR')

	liste_raccourcis = ['drp']

	for raccourci in liste_raccourcis:
		#try:
		pywikibot.output("""
************************************************
|			  TRAITEMENT DE %s			  |
************************************************""" %  raccourci)
		bot = TreatementBot(raccourci = raccourci)
		bot.traitement()
		pywikibot.output("""
************************************************
|		  FIN DU TRAITEMENT DE %s			|
************************************************""" %  raccourci)
		#except Exception, myexception:
		#	pywikibot.output(u'erreur lors du traitement de %s' % raccourci)
		#	pywikibot.output(u'%s %s' % (type(myexception), myexception.args))
		#	continue

if __name__ == '__main__':
	try:
		main()
	except Exception as myexception:
		_errorhandler.handle(myexception)
		raise
	finally:
		pywikibot.stopme()
