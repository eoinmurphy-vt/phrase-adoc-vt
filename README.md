---

## 🧩 Phrase TMS ↔ GitHub Automation Workflow

[![Sync from Repo 1](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/sync-from-repo1.yaml/badge.svg)](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/sync-from-repo1.yaml)

[![AsciiDoc Preprocess](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/preprocess.yml/badge.svg)](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/preprocess.yml)

[![AsciiDoc Postprocess](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/postprocess.yml/badge.svg)](https://github.com/eoinmurphy-vt/phrase-adoc-vt/actions/workflows/postprocess.yml)

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

### 👥 For Translators and Project Managers

* Upload or commit new `.adoc` files to the **`source/`** folder.
* Phrase TMS will automatically detect and import them from the **`processed/`** folder.
* Once translations are complete, the **`translated/`** folder will be updated automatically.
* Within a few minutes, the **`final/`** folder will contain the finalized AsciiDoc files, fully restored and ready for publication.

---

### 🧩 Technical Notes

* Both stages run via [GitHub Actions](https://github.com/features/actions).
* Scripts used:

  * `preprocess_adoc.py`
  * `postprocess_adoc.py`
* Encoding: **Unix-compatible UTF-8**

---