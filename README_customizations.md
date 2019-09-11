# Epicyon Customizations

## Terms of Service

You can customize the terms of service by editing **accounts/tos.txt**. If it doesn't already exist then you can use **default_tos.txt** as a template.

## About Your Instance

Information about your instance and its origin story can be added by editing **accounts/about.txt**.

## Welcome Message

On the login screen you can provide a custom welcome message by creating the file **accounts/login.txt**. This could be used to show a motd or scheduled maintenance information.

## Login Logo

You can customize the image on the login screen by saving your instance logo to **accounts/login.png**. A background image can also be set for the login screen by adding **accounts/login-background.png**

A custom background image can be supplied for the search screen by adding **accounts/search-background.png**

## Reports Advice

When a moderator report is created the message at the top of the screen can be customized to provide any additional information, advice or alerts. Edit **accounts/report.txt** and add your text.

## Extra Emoji

Extra emoji can be added to the *emoji* directory and you should then update the **emoji/emoji.json** file, which maps the name to the filename (without the .png extension).

## Style / Colors

The overall style, including background colors or sizes of things can be changed by making customized css files.

``` bash
cp epicyon-profile.css epicyon.css
cp epicyon-follow.css follow.css
cp epicyon-login.css login.css
cp epicyon-suspended.css suspended.css
```

You can then edit *epicyon.css*, *follow.css*, *login.css* and *follow.css* as needed and those files won't be overwritten if you upgrade.

*epicyon.css* is the main style for displaying profiles and timelines.

*follow.css* is used for displaying options when you select an avatar.

*login.css* defines the style of the login screen.

*suspended.css* is the style for the screen which shows that an account has been suspended.