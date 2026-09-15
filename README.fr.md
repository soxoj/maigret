# Maigret

<div align="center">
  <div>
    <a href="https://pypi.org/project/maigret/">
        <img alt="Version PyPI de Maigret" src="https://img.shields.io/pypi/v/maigret?style=flat-square" />
    </a>
    <a href="https://pepy.tech/project/maigret">
      <img alt="Téléchargements totaux" src="https://static.pepy.tech/badge/maigret" />
      <img alt="Téléchargements par mois" src="https://static.pepy.tech/badge/maigret/month" />
    </a>
  </div>
  <div>
    <a href="https://github.com/soxoj/maigret">
        <img alt="Nombre de vues du projet Maigret" src="https://komarev.com/ghpvc/?username=maigret&color=brightgreen&label=views&style=flat-square" />
    </a>
    <a href="https://github.com/soxoj/maigret">
        <img alt="Version minimale de Python requise : 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-brightgreen?style=flat-square" />
    </a>
    <a href="https://github.com/soxoj/maigret/blob/main/LICENSE">
        <img alt="Licence de Maigret" src="https://img.shields.io/github/license/soxoj/maigret?style=flat-square" />
    </a>
    <a href="https://maigret.readthedocs.io/">
        <img alt="Documentation de Maigret" src="https://img.shields.io/readthedocs/maigret?style=flat-square&label=docs" />
    </a>
  </div>
  <br>
  <div>
    <img src="https://raw.githubusercontent.com/soxoj/maigret/main/static/maigret.png" height="300" alt="Logo de Maigret"/>
  </div>
  <br>
  <div>
    <a href="https://codewiki.google/github.com/soxoj/maigret">
        <img alt="Interroger Code Wiki à propos de Maigret" src="https://img.shields.io/badge/Code_Wiki-ask_about_repo-yellow?logo=googlegemini" />
    </a>
    <a href="https://deepwiki.com/soxoj/maigret">
        <img alt="Interroger DeepWiki à propos de Maigret" src="https://img.shields.io/badge/DeepWiki-ask_about_repo-yellow" />
    </a>
  </div>
  <br>
  <div>
    <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <b>Français</b>
  </div>
  <br>
  <div>
    📖 <a href="https://maigret.readthedocs.io/"><b>Documentation</b></a>
  </div>
  <br>
</div>

**Maigret** rassemble un dossier sur une personne **à partir d'un simple nom d'utilisateur** : il recherche ses comptes sur un très grand nombre de sites et collecte toutes les informations disponibles sur les pages web. Aucune clé d'API n'est nécessaire. **[Profilage par IA (démo)](#ai-analysis)**.

## Sponsors

<p align="center">
  <img width="300" alt="Emplacement de sponsoring principal" src="https://github.com/user-attachments/assets/9ee53377-c817-4a57-90ca-4baa2303bcae" />
</p>

<hr>

<br>

<p align="center">
  <a href="https://www.rapidproxy.io/?ref=soxoj">
    <img src="https://github.com/user-attachments/assets/4ed589d1-37cb-4a40-9273-bff4d6f1a514" width="500" alt="RapidProxy">
  </a>
</p>

<p>
  <a href="https://www.rapidproxy.io/?ref=soxoj"><b>RapidProxy</b></a> fournit des proxys résidentiels performants pour le scraping de Twitter, l'automatisation avec Selenium et l'extraction de données web. Plus de 90 millions d'IP · rotation intelligente · anti-blocage · trafic sans expiration. <br>
<b>Offre spéciale</b> : essai gratuit, formules à partir de 0,65 $/Go. Utilisez le code <b>RAPID10</b> pour 10 % de réduction.
</p>

<p align="center">
  <a href="https://mangoproxy.com/?utm_source=soxoj&utm_medium=partner&utm_campaign=soxoj_github">
    <img src="https://github.com/user-attachments/assets/146b6b95-06ae-4fda-bff2-d94946cf7c2e" width="300" alt="MangoProxy">
  </a>
</p>

<p>
  <a href="https://mangoproxy.com/?utm_source=soxoj&utm_medium=partner&utm_campaign=soxoj_github"><b>MangoProxy</b></a> est un service de proxys résidentiels, ISP, mobiles et de datacenter, conçu pour les usages professionnels où la stabilité, la vitesse et l'anonymat comptent. <br>
<b>Code promo</b> : SOXOJ - 8 % de réduction sur les proxys ISP statiques
</p>

<p align="center">
  <a href="https://www.thordata.com/?ls=dmt&lk=dmt">
    <img src="https://github.com/user-attachments/assets/6d92bda0-c953-49b5-ab7e-73b0e67f17e2" width="350" alt="Thordata">
  </a>
</p>

<p>
  <a href="https://www.thordata.com/?ls=dmt&lk=dmt"><b>Thordata</b></a> fournit des proxys résidentiels fiables pour la recherche OSINT, la recherche de noms d'utilisateur et la collecte de données publiques.
Accédez à <b>plus de 100 millions d'IP résidentielles réelles</b> dans <b>plus de 195 pays</b>, avec des <b>connexions simultanées illimitées</b>, 99,99 % de disponibilité, des connexions stables, des sessions rotatives ou persistantes et un taux de réussite élevé.
<br>
<b>Offre spéciale :</b> 3 jours d'essai gratuit + <b>10 % de réduction</b> avec le code <b>SOXOJ10</b>.

</p>

## Sommaire

- [En une minute](#one-minute)
- [Principales fonctionnalités](#main-features)
- [Démo](#demo)
- [Installation](#installation)
- [Utilisation](#usage)
- [Contribuer](#contributing)
- [Usage commercial](#commercial-use)
- [À propos](#about)

<a id="one-minute"></a>
## En une minute

Assurez-vous d'avoir Python 3.10 ou une version supérieure.

```bash
pip install maigret
maigret VOTRE_NOM_DUTILISATEUR
```

Rien à installer ? Essayez le [bot Telegram communautaire](https://maigret.app/readme-en) ou un [shell cloud](#cloud-shells).

Vous préférez une interface web ? Voir [comment la lancer](#web-interface).

À lire aussi : [Démarrage rapide](https://maigret.readthedocs.io/en/latest/quick-start.html).

<a id="main-features"></a>
## Principales fonctionnalités

- Prend en charge plus de 3 000 sites ([voir la liste complète](https://github.com/soxoj/maigret/blob/main/sites.md)). Une exécution par défaut vérifie les 500 sites les mieux classés par trafic ; passez `-a` pour tout parcourir, ou `--tags` pour restreindre par catégorie ou par pays.
- Intégrable dans vos projets Python : importez `maigret` et lancez des recherches depuis votre code (voir l'[utilisation en tant que bibliothèque](https://maigret.readthedocs.io/en/latest/library-usage.html)).
- [Extrait](https://github.com/soxoj/socid_extractor) toutes les informations disponibles sur le titulaire du compte depuis les pages de profil et les API des sites, y compris les liens vers d'autres comptes.
- Effectue une recherche récursive à partir des noms d'utilisateur et des identifiants découverts.
- Permet de filtrer par tags (catégories de sites, pays).
- Détecte et contourne partiellement les blocages, la censure et les CAPTCHA.
- Récupère à chaque exécution (une fois toutes les 24 heures) une [base de sites mise à jour automatiquement](https://maigret.readthedocs.io/en/latest/settings.html#database-auto-update) depuis GitHub, et se rabat sur la base embarquée en cas de coupure réseau.
- Fonctionne avec les sites Tor et I2P, et sait vérifier des domaines.
- Embarque une [interface web](#web-interface) pour parcourir les résultats sous forme de graphe et télécharger les rapports dans tous les formats depuis une seule page.
- Propose un [mode d'analyse par IA](#ai-analysis) facultatif (`--ai`), qui transforme les résultats bruts en une courte synthèse d'enquête via une API compatible OpenAI.

Pour la liste complète des fonctionnalités, voir la [documentation des fonctionnalités](https://maigret.readthedocs.io/en/latest/features.html).

### Ils utilisent Maigret

Des outils professionnels d'OSINT et d'analyse des réseaux sociaux construits sur Maigret :

<a href="https://github.com/SocialLinks-IO/sociallinks-api"><img height="60" alt="Social Links API" src="https://github.com/user-attachments/assets/789747b2-d7a0-4d4e-8868-ffc4427df660"></a>
<a href="https://sociallinks.io/products/sl-crimewall"><img height="60" alt="Social Links Crimewall" src="https://github.com/user-attachments/assets/0b18f06c-2f38-477b-b946-1be1a632a9d1"></a>
<a href="https://usersearch.ai/"><img height="60" alt="UserSearch" src="https://github.com/user-attachments/assets/66daa213-cf7d-40cf-9267-42f97cf77580"></a>

<a id="demo"></a>
## Démo

### Vidéo

<a href="https://asciinema.org/a/Ao0y7N0TTxpS0pisoprQJdylZ">
  <img src="https://asciinema.org/a/Ao0y7N0TTxpS0pisoprQJdylZ.svg" alt="asciicast" width="600">
</a>

### Rapports

[Rapport PDF](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotographycars.pdf), [rapport HTML](https://htmlpreview.github.io/?https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotographycars.html)

![Capture d'écran d'un rapport HTML](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotography_html_screenshot.png)

![Capture d'écran d'un rapport XMind 8](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotography_xmind_screenshot.png)

[Sortie console complète](https://raw.githubusercontent.com/soxoj/maigret/main/static/recursive_search.md)

<a id="installation"></a>
## Installation

Vous avez déjà suivi les étapes [En une minute](#one-minute) ? C'est tout bon. Voici les autres méthodes possibles.

Vous ne voulez rien installer ? Utilisez le [bot Telegram communautaire](https://maigret.app/readme-en).

### Windows

Téléchargez `maigret_standalone.exe` depuis les [Releases](https://github.com/soxoj/maigret/releases). Deux façons de le lancer :

- **Double-cliquez dessus** : Maigret demandera un nom d'utilisateur, lancera une recherche par défaut et attendra à la fin pour que les liens des rapports restent visibles.
- **Lancez-le depuis un terminal** : ouvrez l'invite de commandes (`Win+R`, tapez `cmd`, Entrée) ou PowerShell pour passer d'autres options :

```cmd
cd %USERPROFILE%\Downloads
maigret_standalone.exe NOMDUTILISATEUR
maigret_standalone.exe NOMDUTILISATEUR --html       :: enregistre aussi un rapport HTML
maigret_standalone.exe --help                       :: liste toutes les options
```

Guide vidéo : https://youtu.be/qIgwTZOmMmM.

<a id="cloud-shells"></a>
### Shells cloud

Lancez Maigret dans le navigateur via un shell cloud ou un notebook Jupyter :

<a href="https://console.cloud.google.com/cloudshell/open?git_repo=https://github.com/soxoj/maigret&tutorial=cloudshell-tutorial.md"><img src="https://user-images.githubusercontent.com/27065646/92304704-8d146d80-ef80-11ea-8c29-0deaabb1c702.png" alt="Ouvrir dans Cloud Shell" height="50"></a>
<a href="https://repl.it/github/soxoj/maigret"><img src="https://replit.com/badge/github/soxoj/maigret" alt="Exécuter sur Replit" height="50"></a>

<a href="https://colab.research.google.com/gist/soxoj/879b51bc3b2f8b695abb054090645000/maigret-collab.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Ouvrir dans Colab" height="45"></a>
<a href="https://mybinder.org/v2/gist/soxoj/9d65c2f4d3bec5dd25949197ea73cf3a/HEAD"><img src="https://mybinder.org/badge_logo.svg" alt="Ouvrir dans Binder" height="45"></a>

### Snap (Linux)

<a href="https://snapcraft.io/maigret"><img src="https://snapcraft.io/static/images/badges/en/snap-store-black.svg" alt="Télécharger depuis le Snap Store" height="50"></a>

```bash
sudo snap install maigret

# utilisation
maigret nomdutilisateur
```

Disponible pour amd64 et arm64, sans Python. Le snap est strictement confiné et peut écrire dans votre répertoire personnel : lancez-le donc depuis celui-ci. Pour les clés USB, connectez l'interface une fois avec `sudo snap connect maigret:removable-media`.

### Installation locale (pip)

```bash
# installation depuis PyPI
pip3 install maigret

# utilisation
maigret nomdutilisateur
```

### Depuis les sources

```bash
# ou clonez le dépôt et installez à la main
git clone https://github.com/soxoj/maigret && cd maigret

# construction et installation
pip3 install .

# utilisation
maigret nomdutilisateur
```

### Docker

Deux variantes d'image sont publiées :

- `soxoj/maigret:latest` — mode ligne de commande (par défaut)
- `soxoj/maigret:web` — lance automatiquement l'[interface web](#web-interface)

```bash
# image officielle (CLI)
docker pull soxoj/maigret

# utilisation en CLI
docker run -v /mydir:/app/reports soxoj/maigret:latest nomdutilisateur --html

# interface web (ouvrir http://localhost:5000)
docker run -p 5000:5000 soxoj/maigret:web

# interface web sur un autre port
docker run -e PORT=8080 -p 8080:8080 soxoj/maigret:web

# construction manuelle
docker build -t maigret .                  # image CLI (cible par défaut)
docker build --target web -t maigret-web . # image de l'interface web
```

### Dépannage

Des erreurs de compilation ? Voir le [guide de dépannage](https://maigret.readthedocs.io/en/latest/installation.html#troubleshooting).

Les rapports PDF (`--pdf`) sont une extension facultative : installez-les avec `pip install 'maigret[pdf]'`. Ils ont besoin de bibliothèques graphiques système sous Linux et macOS ; voir la [section sur les rapports PDF](https://maigret.readthedocs.io/en/latest/installation.html#optional-pdf-reports-maigret-pdf) pour les étapes propres à chaque système.

<a id="usage"></a>
## Utilisation

### Exemples

```bash
# générer des rapports HTML, PDF et XMind
maigret user --html
maigret user --pdf
maigret user --xmind # XML hérité, avec un manifeste pour les lecteurs XMind 2022+

# exports exploitables par une machine
maigret user --json ndjson   # JSON délimité par des sauts de ligne (aussi : --json simple)
maigret user --csv
maigret user --txt
maigret user --graph         # graphe D3 interactif (HTML)
maigret user --neo4j         # script Cypher pour Neo4j (base de données orientée graphe)

# rechercher sur les sites marqués des tags photo et dating
maigret user --tags photo,dating

# rechercher sur les sites marqués du tag us
maigret user --tags us

# mettre en évidence les sites dont la page mentionne aussi certains mots-clés
maigret user --keywords python rust
# les sites correspondants apparaissent avec « [++] » en vert vif

# rechercher trois noms d'utilisateur sur tous les sites disponibles
maigret user1 user2 user3 -a

# synthèse d'enquête assistée par IA (nécessite OPENAI_API_KEY)
maigret user --ai
```

`--neo4j` écrit un script `*_neo4j.cypher` du graphe des résultats ; importez-le avec `cypher-shell -u neo4j -p <mot_de_passe> < report_user_neo4j.cypher` ou collez-le dans le Neo4j Browser. Les réimports sont idempotents. Voir la [documentation de l'export Neo4j](https://maigret.readthedocs.io/en/latest/command-line-options.html#neo4j-export).

Lancez `maigret --help` pour toutes les options. Documentation : [options de ligne de commande](https://maigret.readthedocs.io/en/latest/command-line-options.html), [autres exemples](https://maigret.readthedocs.io/en/latest/usage-examples.html). Vous tombez sur des 403 ou des dépassements de délai ? Voir [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

<a id="web-interface"></a>
### Interface web

Maigret embarque une interface web avec un graphe des résultats et des rapports téléchargeables.

Vous ne voulez pas l'héberger vous-même ? Déployez l'image Docker publiée `soxoj/maigret:web` en un clic :

<a href="https://render.com/deploy?repo=https://github.com/soxoj/maigret&path=utils/render.yaml"><img src="https://render.com/images/deploy-to-render-button.svg" alt="Déployer sur Render" height="40"></a>

Fonctionne sur l'offre gratuite de Render (mise en veille après 15 minutes d'inactivité, redémarrage à la requête suivante). Aucune authentification n'est configurée sur l'instance : toute personne disposant de l'URL peut l'utiliser.

<details>
<summary>Captures d'écran de l'interface web</summary>

![Interface web : comment la démarrer](https://raw.githubusercontent.com/soxoj/maigret/main/static/web_interface_screenshot_start.png)

![Interface web : les résultats](https://raw.githubusercontent.com/soxoj/maigret/main/static/web_interface_screenshot.png)

</details>

```console
maigret --web 5000
```

Ouvrez http://127.0.0.1:5000, saisissez un nom d'utilisateur et consultez les résultats.

### Bibliothèque Python

**Maigret peut être intégré à vos propres projets Python.** La ligne de commande n'est qu'une fine couche au-dessus d'une fonction asynchrone que vous pouvez appeler directement : construisez vos propres chaînes de traitement, alimentez vos outils avec les résultats, ou faites tourner Maigret au sein d'un workflow OSINT plus large.

Voir le [guide d'utilisation en tant que bibliothèque](https://maigret.readthedocs.io/en/latest/library-usage.html) pour un exemple complet, les usages asynchrones et le filtrage des sites par tag.

### Options utiles en ligne de commande

- `--parse URL` — analyse une page de profil, en extrait les identifiants et noms d'utilisateur, puis s'en sert pour lancer une recherche récursive.
- `--permute` — génère les variantes probables d'un nom d'utilisateur à partir de deux entrées ou plus (par exemple `john doe` → `johndoe`, `j.doe`, etc.) et les recherche toutes.
- `--self-check [--auto-disable]` — vérifie les paires `usernameClaimed` / `usernameUnclaimed` sur les sites réels, pour les mainteneurs qui auditent la base.
- `--ai` / `--ai-model` — lance l'[analyse par IA](#ai-analysis) sur les résultats et diffuse une courte synthèse d'enquête dans le terminal.

<a id="ai-analysis"></a>
### Analyse par IA

[![asciicast](https://asciinema.org/a/979404.svg)](https://asciinema.org/a/979404)

`--ai` rassemble les résultats de la recherche, construit un rapport Markdown interne et l'envoie à un point d'entrée de complétion de conversation compatible OpenAI, afin de produire une courte synthèse d'enquête neutre (nom réel probable, localisation, profession, centres d'intérêt, langues, indice de confiance, pistes à creuser). La progression site par site est masquée et la réponse du modèle est diffusée sur la sortie standard.

```bash
export OPENAI_API_KEY=sk-...
maigret user --ai

# choisir un autre modèle
maigret user --ai --ai-model gpt-4o-mini
```

La clé peut aussi être définie via `openai_api_key` dans `settings.json`. Le point d'entrée vaut par défaut `https://api.openai.com/v1`, mais `openai_api_base_url` dans `settings.json` peut désigner n'importe quelle API compatible OpenAI (Azure OpenAI, OpenRouter, un serveur local, etc.). Voir la [documentation des paramètres](https://maigret.readthedocs.io/en/latest/settings.html) pour la liste complète des options.

### Tor / I2P / proxys

Maigret peut faire passer ses vérifications par un proxy, par Tor ou par I2P, ce qui est utile pour les sites `.onion` et `.i2p` et pour contourner les WAF qui bloquent les IP de datacenter.

```bash
# n'importe quel proxy HTTP/SOCKS
maigret user --proxy socks5://127.0.0.1:1080

# Tor (passerelle par défaut socks5://127.0.0.1:9050)
maigret user --tor-proxy socks5://127.0.0.1:9050

# I2P (passerelle par défaut http://127.0.0.1:4444)
maigret user --i2p-proxy http://127.0.0.1:4444
```

Démarrez votre démon Tor ou I2P avant de lancer la commande : Maigret ne gère pas ces passerelles.

### Contournement de Cloudflare

> **Expérimental.** Le webgate Cloudflare est en cours de développement actif ; le schéma de configuration, le comportement en ligne de commande et l'ensemble des sites routés peuvent changer sans garantie de compatibilité ascendante.

Une partie des sites de la base exigent un vrai navigateur pour résoudre un défi JavaScript. Maigret peut déléguer ces vérifications à une instance locale de [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) :

```bash
docker run -d -p 8191:8191 --name flaresolverr ghcr.io/flaresolverr/flaresolverr:latest
maigret --cloudflare-bypass <nomdutilisateur>
```

Le contournement est facultatif (`--cloudflare-bypass`, ou `cloudflare_bypass.enabled` dans `settings.json`) et ne se déclenche que pour les sites dont le champ `protection` correspond. Voir la [documentation de la fonctionnalité](https://maigret.readthedocs.io/en/latest/features.html#cloudflare-bypass) pour les options de backend et la configuration.

<a id="contributing"></a>
## Contribuer

Ajoutez ou corrigez des sites de façon chirurgicale dans `data.json` (sans `json.load` / `json.dump`), puis lancez `./utils/update_site_data.py` pour regénérer `sites.md` et les métadonnées de la base, et ouvrez une pull request. Pour plus de détails, voir le [guide CONTRIBUTING](https://github.com/soxoj/maigret/blob/main/CONTRIBUTING.md) et la [documentation de développement](https://maigret.readthedocs.io/en/latest/development.html). Historique des versions : [CHANGELOG.md](CHANGELOG.md).

<a id="commercial-use"></a>
## Usage commercial

Maigret est open source, sous licence MIT, et son usage commercial est libre et sans restriction. Mais les vérifications de sites se cassent avec le temps et demandent une maintenance active.

Pour un usage commercial sérieux, avec une **base de sites mise à jour quotidiennement** ou une **API de vérification de noms d'utilisateur**, écrivez-nous : 📧 [maigret@soxoj.com](mailto:maigret@soxoj.com)

- Base de sites privée — plus de 5 000 sites, mise à jour chaque jour (distincte de la base open source publique)
- API de vérification de noms d'utilisateur — pour intégrer Maigret à votre produit

<a id="about"></a>
## À propos

### Avertissement

**À usage éducatif et légal uniquement.** Il vous appartient de respecter toutes les lois applicables dans votre juridiction (RGPD, CCPA, etc.). Les auteurs déclinent toute responsabilité en cas d'usage abusif.

### Retours

[Ouvrir une issue](https://github.com/soxoj/maigret/issues) · [GitHub Discussions](https://github.com/soxoj/maigret/discussions) · [Telegram](https://t.me/soxoj)

### Classification SOWEL

Techniques OSINT utilisées :
- [SOTL-2.2. Search For Accounts On Other Platforms](https://sowel.soxoj.com/other-platform-accounts)
- [SOTL-6.1. Check Logins Reuse To Find Another Account](https://sowel.soxoj.com/logins-reuse)
- [SOTL-6.2. Check Nicknames Reuse To Find Another Account](https://sowel.soxoj.com/nicknames-reuse)

### Licence

MIT © [Maigret](https://github.com/soxoj/maigret)
