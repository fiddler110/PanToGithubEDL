# Branch Protection Configuration

Enforce EDL validation as a required check before any PR can be merged into `main`.

---

## GitHub

### 1 — Run the workflow at least once

Push the `validate-edl.yml` workflow to `main` and open a test PR. GitHub only
lists a status check as selectable once it has run at least once.

### 2 — Add a branch protection rule

1. Navigate to **Settings → Branches** in your repository.
2. Under **Branch protection rules**, click **Add rule**.
3. Set **Branch name pattern** to `main`.

### 3 — Configure the rule

Enable the following options:

| Option | Setting |
|---|---|
| Require a pull request before merging | ✅ On |
| Require status checks to pass before merging | ✅ On |
| Require branches to be up to date before merging | ✅ On (recommended) |
| Do not allow bypassing the above settings | ✅ On (recommended) |

### 4 — Add the required status check

Under **Status checks that are required**, search for:

```
Validate External Dynamic Lists
```

This name comes from the `name:` field of the job in `.github/workflows/validate-edl.yml`.
Select it from the dropdown and click **Save changes**.

### Result

All PRs targeting `main` must now pass the EDL validator before the merge button
becomes active. Direct pushes to `main` are blocked.

---

## Azure DevOps

Azure DevOps uses **Branch Policies** rather than branch protection rules.
An additional pipeline definition file is required.

### 1 — Add the Azure Pipelines definition

Create the file `azure-pipelines.yml` in the root of the repository:

```yaml
trigger: none

pool:
  vmImage: ubuntu-latest

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: "3.11"
    displayName: Set up Python

  - script: python validate_edl.py
    displayName: Validate EDL Files
```

Commit and push this file to `main`.

### 2 — Create the pipeline

1. In your Azure DevOps project, go to **Pipelines → New pipeline**.
2. Select your repository source (Azure Repos Git or GitHub).
3. Choose **Existing Azure Pipelines YAML file** and select `azure-pipelines.yml`.
4. Click **Save** (do not run it yet).
5. Note the pipeline name — you will reference it in the next step.

### 3 — Configure the branch policy

1. Go to **Repos → Branches**.
2. Hover over the `main` branch, click the **⋯** menu, and select **Branch policies**.
3. Under **Build Validation**, click **+**.
4. Set the following:

| Field | Value |
|---|---|
| Build pipeline | Select the pipeline you created above |
| Trigger | Automatic |
| Policy requirement | Required |
| Build expiration | Immediately when `main` is updated |
| Display name | `Validate EDL Files` |

5. Click **Save**.

### 4 — Block direct pushes to main

Still on the Branch policies page, also enable:

| Policy | Setting |
|---|---|
| Require a minimum number of reviewers | 1 (recommended) |
| Check for linked work items | Optional |
| Require approval from additional services | Optional |

> Azure DevOps enforces branch policies automatically — once a Required build
> policy exists, direct pushes to `main` are blocked for all users including
> project administrators unless the policy is temporarily disabled.

### Result

Every PR targeting `main` triggers the `azure-pipelines.yml` pipeline. The PR
cannot be completed until the EDL validator exits with code 0.
