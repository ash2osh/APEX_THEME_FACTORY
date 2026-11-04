# Put the demo online

This guide puts a live demo of all eight themes on public APEX hosting, so people can try them before they install
anything. It takes about 30 minutes, most of it waiting for a workspace.

The demo is Oracle's Universal Theme Reference app with all the themes added. Visitors open a gallery of the themes,
switch between them with the **Theme** menu, and browse about 120 pages of real components. Their theme choice stays
in their own browser.

## What you need

| Item | Notes |
|---|---|
| `theme-factory-demo.zip` | Download it from the [Releases page](https://github.com/ash2osh/APEX_THEME_FACTORY/releases), or build it. See Step 1. |
| An APEX workspace on APEX 26.1 or newer | Step 2 lists the options. |
| Permission to host a public app | Check the terms of your hosting. See Step 2. |

## Step 1: Get the ZIP

If you downloaded the ZIP from the Releases page, go to Step 2. To build it yourself from this repository:

```bash
scripts/build-demo.sh
```

In Windows PowerShell, run `powershell -ExecutionPolicy Bypass -File .\scripts\build-demo.ps1`.

This writes `dist/demo/theme-factory-demo.zip`. It changes only the copy that goes into the ZIP, and each build gets
a new session-state protection salt.

## Step 2: Get a workspace

Pick one of these:

| Option | Good for | Before you choose it |
|---|---|---|
| Free workspace at [apex.oracle.com](https://apex.oracle.com) | Trying the demo, or a short-lived link | Oracle offers these for evaluation. Read the current terms when you sign up, and check that a public demo is allowed. It can be slower, and it can run a preview release. |
| Always Free [Oracle Autonomous Database](https://www.oracle.com/autonomous-database/free-trial/) | A demo you want to keep online | It takes longer to set up. |
| Your own APEX server | Full control | You look after security and updates. Put it behind HTTPS. |

To check the version, sign in and look at the bottom of the App Builder page, or run this in **SQL Workshop**:

```sql
select version_no from apex_release;
```

It must be 26.1 or newer, because the app can't be imported into an older version.

## Step 3: Import the app

1. In **App Builder**, click **Import**.
2. Upload `theme-factory-demo.zip`, and continue through the wizard.
3. If the wizard asks about the application ID, choose **Auto Assign New Application ID**.
4. If the wizard offers to install supporting objects, choose **Yes**, and then skip Step 4.
5. Note the new application ID at the end.

If you have SQLcl and a saved connection, you can import it this way instead, using an ID that's free:

```bash
sql -name <CONNECTION>
```

```sql
apex import -input theme-factory-demo.zip -workspace <WORKSPACE> -id <NEW_APP_ID>
```

## Step 4: Install the sample data

About 20 pages show sample data from tables named `EBA_UT_*`. Without those tables they show an ORA-00942 error, and
the rest of the demo still works.

1. Open the app in App Builder and click **Supporting Objects**.
2. Click **Install Supporting Objects**, choose **Yes**, and finish the wizard.

This creates the tables in your workspace's schema, so use a workspace that doesn't already hold important data.

If the install isn't offered, run the two scripts in `supporting-objects/install-scripts/` from the ZIP in
**SQL Workshop > SQL Scripts**: `create-tables.sql` first, and then `create-airports-table.sql`.

## Step 5: Check it as a visitor

Sign out of App Builder, or use a private browser window, and open:

```text
https://<YOUR_HOST>/ords/r/<WORKSPACE>/theme-factory-demo/themes
```

Check these points:

- The theme gallery opens without a sign-in page.
- The **Theme** menu changes the theme, and your choice is still there after a reload.
- **Components > Interactive Report** shows data, and the page has no red error messages.
- On a phone, or in a narrow window, the pages fit the screen without sideways scrolling.
- The notice at the bottom of the gallery says the demo isn't affiliated with Oracle. Please keep this notice.

Dialog pages such as 1111 show an error if you open their URL directly. That comes from Oracle's sample app. The
dialogs work when you open them from their normal buttons.

## Step 6: Share it

Link to the gallery, using the URL from Step 5. Add `#theme=<name>` to open a specific theme on a visitor's first
page load, for example `.../theme-factory-demo/themes#theme=solarized-dark`. The names are the folder names in
`sample-themes/`.

To show the link in this project, add it to the top of `README.md`.

## What visitors can and can't do

We reviewed the app for public use. It has these properties:

- **No data changes.** No page process writes to the database, and no page sends email or calls out to other servers.
- **Uploads are not stored.** The file-upload items on the form demo pages have no process behind them.
- **No sign-in needed.** Every page is public. The login page is there but nothing depends on it.
- **No changes to the app.** The demo turns off runtime changes to the application.

They can sort and filter reports for themselves, and those settings end with their session. Anyone can read the app's
public pages, so don't add private data to this workspace's demo tables. Your hosting's own limits and rate limits
still apply.

The maps on page 1906 load map tiles from the internet, so they need the visitor's browser to reach the tile service.

## Update or remove the demo

**To update it,** build or download the new ZIP and repeat Step 3, this time entering the ID of your existing demo so
it gets replaced (**Change Application ID** in the wizard, or `-id` in SQLcl). Visitors' open sessions end when you do this.

**To remove it,** open the app in App Builder and click **Delete Application**. To remove the sample tables as well,
go to **Supporting Objects**, and choose **Deinstall**.

## If something goes wrong

| What you see | What to do |
|---|---|
| The import says the application alias or ID is in use | An earlier copy is there. Enter its ID so it gets replaced, or delete it first. |
| The import says the theme or version isn't supported | The workspace is older than APEX 26.1. Use a newer one. |
| A sign-in page appears for visitors | Check that you used the `/r/` URL from Step 5. Then check **Shared Components > Security** in the app. |
| Pages show ORA-00942 | Do Step 4. |
| The airports script fails | Your database may lack spatial types. The rest of the sample data still works, and only the map pages are affected. |
| The themes don't appear | Open the browser's developer tools. `css/app.css` should load without errors. If it doesn't, import the ZIP again. |

## What has been tested

The ZIP was imported with SQLcl, and the app and its sample-data scripts were checked on APEX 26.1 and 26.2. App
Builder's upload page and its **Install Supporting Objects** wizard weren't run. The ZIP has the same layout as
Oracle's own sample-app ZIPs, which Oracle documents for that page. If the wizard behaves differently from Step 3 or
Step 4, follow what it shows and please open an issue.

## Licences

The app is based on Oracle's Universal Theme Reference sample, which Oracle publishes under the Universal Permissive
License 1.0. The themes are MIT licensed, and the fonts use the SIL Open Font License. [NOTICE.md](../NOTICE.md) has
the details. Oracle, APEX and Universal Theme are trademarks of Oracle and/or its affiliates.
