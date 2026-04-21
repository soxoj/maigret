.. _use-case-crypto:

Cryptocurrency & Web3 Investigations
=====================================

Blockchain transactions are public, but the people behind wallets are not. Maigret helps bridge this gap by finding Web3 accounts tied to a username, revealing the person behind a pseudonymous crypto persona.

Why it matters
--------------

Crypto investigations often start with a wallet address or an ENS name but hit a wall — the blockchain tells you *what* happened, not *who* did it. A username, however, is reused across platforms. If someone trades on OpenSea as ``zachxbt`` and posts on Warpcast as ``zachxbt``, Maigret connects the dots and builds a full profile.

Common scenarios:

- **Scam attribution.** A rug-pull promoter uses the same alias on Fragment (Telegram username marketplace), OpenSea, and a personal blog.
- **Sanctions compliance.** Verifying whether a counterparty's online footprint matches known sanctioned individuals.
- **Due diligence.** Before an OTC deal or DAO vote, checking whether the other party has a consistent online presence or is a freshly created sockpuppet.
- **Stolen funds tracing.** A stolen NFT appears on OpenSea under a new account — but the username matches a Warpcast profile with real-world links.

Supported sites
---------------

Maigret currently checks the following crypto and Web3 platforms:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Site
     - What it reveals
     - Notes
   * - **OpenSea**
     - NFT collections, trading history, profile bio, linked website
     -
   * - **Rarible**
     - NFT marketplace profile, collections, listing history
     - Complements OpenSea for NFT attribution across marketplaces
   * - **Zora**
     - Zora Network profile, minted NFTs, creator activity
     - Ethereum L2 creator platform; useful for on-chain art attribution
   * - **Polymarket**
     - Prediction-market profile, positions, public portfolio P&L
     - Useful for political/financial prediction attribution
   * - **Warpcast** (Farcaster)
     - Decentralized social profile, posts, follower graph, Farcaster ID
     - Every Farcaster ID maps to an Ethereum address via the on-chain ID registry
   * - **Fragment**
     - Telegram username ownership, TON wallet address, purchase date and price
     - Valuable for linking Telegram identities to TON wallets
   * - **Paragraph**
     - Web3 blog/newsletter, ETH wallet address, linked Twitter handle
     - Richest cross-platform data among crypto sites
   * - **Tonometerbot**
     - TON wallet balance, subscriber count, NFT collection, rankings
     - TON blockchain analytics
   * - **Spatial**
     - Metaverse profile, linked social accounts (Discord, Twitter, Instagram, LinkedIn, TikTok)
     - Rich cross-platform links
   * - **Revolut.me**
     - Payment handle: first/last name, country code, base currency, supported payment methods
     - Not strictly Web3, but widely used by crypto OTC traders for fiat off-ramps; the public API returns structured KYC-adjacent data

Real-world example: zachxbt
---------------------------

`ZachXBT <https://twitter.com/zachxbt>`_ is a well-known on-chain investigator. Let's see what Maigret can find from just the username ``zachxbt``:

.. code-block:: console

   maigret zachxbt --tags crypto

Maigret finds 5 accounts and automatically extracts structured data from each:

**Fragment** — confirms the Telegram username ``@zachxbt`` is claimed, reveals the TON wallet address (``EQBisZrk...``), purchase price (10 TON), and date (January 2023).

**Paragraph** — the richest result. Returns the real name used on the platform (``ZachXBT``), bio (``Scam survivor turned 2D investigator``), an Ethereum wallet address (``0x23dBf066...``), and a linked Twitter handle (``zachxbt``). The ``wallet_address`` field is especially valuable — it directly links the pseudonym to an on-chain identity.

**Warpcast** — Farcaster profile with a Farcaster ID (``fid: 20931``), profile image, and social graph (33K followers). Every Farcaster ID is tied to an Ethereum address via the on-chain ID registry, so this is another on-chain anchor.

**OpenSea** — NFT marketplace profile with bio (``On-chain sleuth | 10x rug pull survivor``), avatar (hosted on ``seadn.io`` with an Ethereum address in the URL path), and a link to an external investigations page.

**Hive Blog** — blockchain-based blog account created in March 2025. Low activity (1 post), but confirms the username is claimed across blockchain ecosystems.

From a single username, Maigret produces:

- **2 wallet addresses** — one TON (from Fragment), one Ethereum (from Paragraph)
- **1 confirmed Twitter handle** — ``zachxbt`` (from Paragraph)
- **1 Telegram username** — ``@zachxbt`` (from Fragment)
- **1 external link** — ``investigations.notion.site`` (from OpenSea)
- **Social graph data** — 33K Farcaster followers, blog activity timestamps

This is enough to pivot into blockchain analysis tools (Etherscan, Arkham, Nansen) using the wallet addresses, or into social media analysis using the Twitter handle.

Workflow: from username to wallet
---------------------------------

**Step 1: Search crypto platforms**

.. code-block:: console

   maigret <username> --tags crypto -v

Review the results. Pay attention to:

- **Fragment** — if the username is claimed, you get a TON wallet address directly.
- **Paragraph** — blog profiles often contain an ETH address and a Twitter handle.
- **Warpcast** — Farcaster IDs map to Ethereum addresses via the on-chain registry.
- **OpenSea** — avatar URLs sometimes contain wallet addresses in the path.

**Step 2: Expand with extracted identifiers**

Maigret automatically extracts additional identifiers from found profiles (real names, linked accounts, profile URLs) and recursively searches for them. This is enabled by default. If Maigret finds a linked Twitter handle on a Paragraph profile, it will automatically search for that handle across all sites.

**Step 3: Cross-reference with non-crypto platforms**

The real power is connecting crypto personas to mainstream accounts. Drop the tag filter:

.. code-block:: console

   maigret <username> -a

This checks all 3000+ sites. A match on GitHub, Reddit, or a forum can reveal the person behind the wallet.

Workflow: from wallet to identity
---------------------------------

If you start with a wallet address rather than a username, you can use complementary tools to get a username first:

1. **ENS / Unstoppable Domains** — resolve the wallet address to a human-readable name (``vitalik.eth``). Then search that name in Maigret.
2. **Etherscan labels** — check if the address has a public label (exchange, known entity).
3. **Fragment** — search the TON wallet address to find which Telegram usernames it purchased.
4. **Arkham Intelligence / Nansen** — blockchain attribution platforms that may tag the address with a known identity.

Once you have a username candidate, feed it to Maigret.

Tips
----

- **Username reuse is the #1 signal.** Crypto-native users often reuse their ENS name (``alice.eth``) or a variation (``alice_eth``, ``aliceeth``) across platforms. Try all variations.
- **Fragment is uniquely valuable** because it directly links Telegram usernames to TON wallet addresses — a rare on-chain / off-chain bridge.
- **Warpcast profiles are Ethereum-native.** Every Farcaster account is tied to an Ethereum address via the ID registry contract. If you find a Warpcast profile, you implicitly have a wallet address.
- **Paragraph often has the richest data** — wallet address, Twitter handle, bio, and activity timestamps in a single API response.
- **Use** ``--exclude-tags`` **to skip irrelevant sites** when you're focused on crypto:

  .. code-block:: console

     maigret alice_eth --exclude-tags porn,dating,forum
