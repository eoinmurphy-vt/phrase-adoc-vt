---

## 🧩 Phrase TMS ↔ GitHub Automation Workflow

[![Sync from Repo 1](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/sync-from-repo1.yaml/badge.svg)](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/sync-from-repo1.yaml)

[![AsciiDoc Preprocess](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/preprocess.yaml/badge.svg)](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/preprocess.yaml)

[![AsciiDoc Postprocess](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/postprocess.yaml/badge.svg)](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/postprocess.yaml)

[![Sync to Repo 1](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/sync-to-repo1.yaml/badge.svg)](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/sync-to-repo1.yaml)

### 🔄 Overview

This repository is integrated with **Phrase TMS** to fully automate the translation lifecycle of AsciiDoc files.
It ensures consistent formatting, automatic preprocessing before translation, and automatic restoration afterward.

---

### ⚙️ Folder Structure

| Folder            | Purpose                                                        |
| ----------------- | -------------------------------------------------------------- |
| **`source/`**     | Original AsciiDoc files before translation                     |
| **`processed/`**  | Preprocessed UTF-8 files prepared for Phrase TMS               |
| **`translated/`** | Folder where Phrase TMS commits completed translations         |
| **`final/`**      | Final postprocessed files restored to original AsciiDoc format |

---

### 🧠 Automation Logic

1. **Preprocessing Stage**

   * Trigger: when `.adoc` files are pushed to the `source/` folder
   * Converts files to UTF-8
   * Changes *Simple Monospaced* → *Literal Monospaced* formatting

     * Example:

       ```adoc
       `.NET Library System.Formats.Abcd` → `+.NET Library System.Formats.Abcd+`
       ```
   * Converts `[monospaced]#text#` → `[literal]#text#`
   * Saves results in `processed/` for Phrase TMS to pull

2. **Translation Stage (in Phrase TMS)**

   * Phrase TMS syncs the `processed/` folder as the **source**
   * Translators work directly in Phrase TMS
   * When translation is complete, Phrase TMS pushes the files to the `translated/` folder in GitHub

3. **Postprocessing Stage**

   * Trigger: when `.adoc` files are pushed to the `translated/` folder
   * Reverts all preprocessing changes so files match the original AsciiDoc style

     * Example:

       ```adoc
       `+.NET Library System.Formats.Abcd+` → `.NET Library System.Formats.Abcd`
       ```
   * Converts `[literal]#text#` → `[monospaced]#text#`
   * Force all `AsciiDoc files` to use `Unix LF` newlines
   * Writes clean, final files into the `final/` folder

---

### 🚦 Automation Status

The badge above shows the current automation state:

| Status         | Meaning                                                                    |
| -------------- | -------------------------------------------------------------------------- |
| 🟢 **Passing** | The most recent preprocessing or postprocessing job completed successfully |
| 🔴 **Failing** | The workflow encountered an error — check the *Actions* tab for logs       |

---

### 📂 Repository Structure

Ensure your project follows this structure to support the scripts:

.
├── .github/+
│   └── workflows/+
│       ├── push_to_phrase.yml      # Triggered on push to main+
│       └── pull_from_phrase.yml    # Triggered on phrase updates+
├── scripts/+
│   ├── preprocess_adoc.py          # The Protection Script+
│   └── postprocess_adoc.py         # The Restoration Script+
├── source/                         # Source English files+
├── logs/                           # Execution logs+
└── requirements.txt                # Python dependencies+

---

### 👥 For Translators and Project Managers

* Upload or commit new `.adoc` files to the **`source/`** folder.
* Phrase TMS will automatically detect and import them from the **`processed/`** folder.
* Once translations are complete, the **`translated/`** folder will be updated automatically.
* Within a few minutes, the **`final/`** folder will contain the finalized AsciiDoc files, fully restored and ready for publication.

---

### ⚙️ Configuration & Admin Guide

This workflow uses GitHub Actions Variables to manage repository connections and folder paths. This allows administrators to change configuration (like switching to a new target repository or changing folder names) without editing any code.

1. **How to Change Settings**

   * Navigate to the main page of this repository.
   * Click the Settings tab in the top navigation bar.
   * In the left sidebar, locate the Security section (sometimes labeled Secrets and variables).
   * Click Actions.
   * Select the Variables tab (ensure you are not on the "Secrets" tab).
   * To change a setting, click the pencil icon (Edit) next to the variable.
   * To add a missing setting, click New repository variable.

2. **Available Variables**

If these variables are not set, the workflow will use the Default Values listed below.

| Variable Name             | Default Value    | Description                                                                                         |
| ------------------------- | ---------------- | --------------------------------------------------------------------------------------------------- |
| **`CONTENT_DIR`**         | source           | The local folder where English .adoc files are stored.                                              |
| **`TRANSLATED_DIR`**      | translated       | The folder where Phrase TMS pushes translated files.                                                |
| **`FINAL_DIR`**           | final            | The folder where the final, cleaned AsciiDoc files are saved.                                       |
| **`CURRENT_REPO_NAME`**   | (Your Repo)      | The owner/repo string of this repository (e.g., my-org/docs-connector). Used for dispatch triggers. |
| **`EXTERNAL_REPO_URL`**   | (Client Repo)    | The owner/repo string of the external repository you are syncing with (e.g., client-org/main-docs). |
| **`EXTERNAL_WATCH_PATH`** | docs/modules/en/ | The specific subfolder in the External Repo to watch for changes.                                   |
| **`EXTERNAL_TARGET_DIR`** | docs             | The specific subfolder in the External Repo where finished translations should be pushed.           |

---

### ⚠️ Important Limitations

   * While most settings are configurable via the Variables UI, specific GitHub architecture limitations require the following to be changed manually in the YAML files if updated:
   * Schedules: The sync frequency (e.g., */15 * * * *) must be edited in .github/workflows/sync-from-repo1.yaml.
   * Trigger Paths: If you rename the source or translated folders, you must manually update the paths: filters in preprocess.yaml and postprocess.yaml so the workflows trigger correctly.

---

### 🧩 Technical Notes

* Both stages run via [GitHub Actions](https://github.com/features/actions).
* Scripts used:

  * `preprocess_adoc.py`
  * `postprocess_adoc.py`
* Encoding: **Unix-compatible UTF-8**

---

### 📝 License

This project is licensed under the MIT License.

---