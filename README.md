# Maigret

<p align="center">
  <img src="maigret.png" />
</p>

<i>The Commissioner Jules Maigret is a fictional French police detective, created by Georges Simenon. His investigation method is based on understanding the personality of different people and their interactions.</i>

## About

This is a [sherlock](https://github.com/sherlock-project/) fork with cool features under heavy development.
Don't forget to update source code from repo.

Currently supported [>500 sites](/sites.md), the list grows every day.

## Main features

* Profile pages parsing, [extracting](https://github.com/soxoj/socid_extractor) personal info, links to other profiles, etc.
* Recursive search by new usernames found
* Search by tags (site categories, countries)
* Censorship and captcha detection
* Very few false positives

## Installation

**NOTE**: Python 3.6 or higher and pip is required.

```bash
# clone the repo and change directory
$ git clone https://github.com/soxoj/maigret && cd maigret

# install the requirements
$ python3 -m pip install -r requirements.txt
```

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.png)](https://console.cloud.google.com/cloudshell/open?git_repo=https://github.com/soxoj/maigret&tutorial=README.md)

## Demo with page parsing and recursive username search

![example animation](./images/example.svg)

Listing:
```bash
python3 maigret --ids --print-found --skip-errors alexaimephotographycars
[*] Checking username alexaimephotographycars on:
[+] 500px: https://500px.com/p/alexaimephotographycars
 ┣╸uid: dXJpOm5vZGU6VXNlcjoyNjQwMzQxNQ==
 ┣╸legacy_id: 26403415
 ┣╸username: alexaimephotographycars
 ┣╸name: Alex Aimé
 ┣╸website: www.flickr.com/photos/alexaimephotography/
 ┣╸facebook_link:  www.instagram.com/street.reality.photography/
 ┣╸instagram_username: alexaimephotography
 ┗╸twitter_username: Alexaimephotogr
[*] Checking username alexaimephotography on:
[+] DeviantART: https://alexaimephotography.deviantart.com
 ┣╸country: France
 ┣╸registered_for_seconds: 55040868
 ┣╸gender: male
 ┣╸username: Alexaimephotography
 ┣╸twitter_username: alexaimephotogr
 ┣╸website: www.instagram.com/alexaimephotography/
 ┗╸links:
   ┗╸ https://www.instagram.com/alexaimephotography/
[+] EyeEm: https://www.eyeem.com/u/alexaimephotography
 ┣╸eyeem_id: 21974802
 ┣╸eyeem_username: alexaimephotography
 ┣╸fullname: Alex
 ┣╸followers: 10
 ┣╸friends: 2
 ┣╸liked_photos: 37
 ┣╸photos: 10
 ┗╸facebook_uid: 1534915183474093
[+] Facebook: https://www.facebook.com/alexaimephotography
[+] Gramho: https://gramho.com/explore-hashtag/alexaimephotography
[+] Instagram: https://www.instagram.com/alexaimephotography
 ┣╸username: alexaimephotography
 ┣╸full_name: Alexaimephotography
 ┣╸id: 6828488620
 ┣╸biography: 🇮🇹 🇲🇫 🇩🇪
Amateur photographer
Follow me @street.reality.photography
Sony A7ii
 ┗╸external_url: https://www.flickr.com/photos/alexaimephotography2020/
[+] Picuki: https://www.picuki.com/profile/alexaimephotography
[+] Pinterest: https://www.pinterest.com/alexaimephotography/
 ┣╸pinterest_username: alexaimephotography
 ┣╸fullname: alexaimephotography
 ┣╸image: https://s.pinimg.com/images/user/default_280.png
 ┣╸board_count: 3
 ┣╸pin_count: 4
 ┣╸country: FR
 ┣╸follower_count: 0
 ┣╸following_count: 1
 ┣╸is_website_verified: False
 ┣╸is_indexed: True
 ┣╸is_verified_merchant: False
 ┗╸locale: fr
[+] Reddit: https://www.reddit.com/user/alexaimephotography
 ┣╸reddit_id: t5_1nytpy
 ┣╸reddit_username: alexaimephotography
 ┣╸display_name: alexaimephotography
 ┣╸is_employee: False
 ┣╸is_nsfw: False
 ┣╸is_mod: True
 ┣╸is_following: True
 ┣╸has_user_profile: True
 ┣╸hide_from_robots: False
 ┣╸created_utc: 1562750403
 ┣╸total_karma: 43075
 ┗╸post_karma: 42574
[+] Tumblr: https://alexaimephotography.tumblr.com/
[+] VK: https://vk.com/alexaimephotography
[+] Vimeo: https://vimeo.com/alexaimephotography
 ┣╸uid: 75857717
 ┣╸name: AlexAimePhotography
 ┣╸username: alexaimephotography
 ┣╸location: France
 ┣╸created_at: 2017-12-06 06:49:28
 ┣╸is_staff: False
 ┗╸links:
   ┣╸ https://500px.com/alexaimephotography
   ┣╸ https://www.flickr.com/photos/photoambiance/
   ┣╸ https://www.instagram.com/alexaimephotography/
   ┣╸ https://www.youtube.com/channel/UC4NiYV3Yqih2WHcwKg4uPuQ
   ┗╸ https://flii.by/alexaimephotography/
[+] We Heart It: https://weheartit.com/alexaimephotography
[*] Checking username Alexaimephotogr on:
[+] Twitter: https://twitter.com/Alexaimephotogr
```

## License

MIT © Maigret<br/>
MIT © [Sherlock Project](https://github.com/sherlock-project/)<br/>
Original Creator of Sherlock Project - [Siddharth Dushantha](https://github.com/sdushantha)
