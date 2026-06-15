# README

## List to URL Mapping

| List                  | URL                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------- |
| allow_ip.txt          | https://raw.githubusercontent.com/fiddler110/PanToGithubEDL/refs/heads/main/allow_ip.txt          |
| deny_ip.txt           | https://raw.githubusercontent.com/fiddler110/PanToGithubEDL/refs/heads/main/deny_ip.txt           |
| ssl_bypass_domain.txt | https://raw.githubusercontent.com/fiddler110/PanToGithubEDL/refs/heads/main/ssl_bypass_domain.txt |
| whitelist_domain.txt  | https://raw.githubusercontent.com/fiddler110/PanToGithubEDL/refs/heads/main/whitelist_domain.txt  |

#### allow_ip

```md
https://raw.githubusercontent.com/fiddler110/PanToGithubEDL/refs/heads/main/allow_ip.txt
```

#### deny_ip

```
https://raw.githubusercontent.com/fiddler110/PanToGithubEDL/refs/heads/main/deny_ip.txt
```

#### ssl_bypass_domain

```
https://raw.githubusercontent.com/fiddler110/PanToGithubEDL/refs/heads/main/ssl_bypass_domain.txt
```

#### whitelist_domain

```
https://raw.githubusercontent.com/fiddler110/PanToGithubEDL/refs/heads/main/whitelist_domain.txt
```

## Google Instructions

To pull an External Dynamic List (EDL) from GitHub or Azure DevOps using authentication, you must configure Basic Authentication on the firewall. Because both platforms require secure API authentication (using tokens) instead of standard passwords, you need to configure an HTTP credential profile within PAN-OS.

1. Generate an Authentication TokenGitHub:
   - Generate a Personal Access Token (PAT) under Settings > Developer Settings > Personal Access Tokens. The token only requires the repo scope to read repository contents.
   - Azure DevOps: Generate a PAT under User Settings > Personal Access Tokens with Code (Read) permissions.
2. Configure a Certificate Profile (Highly Recommended)
   - Both GitHub and Azure DevOps use HTTPS. Palo Alto requires the server's certificate to be trusted before passing credentials.
   - Download the root CA certificate used by the platform (e.g., DigiCert certificates for GitHub).
   - Go to Device > Certificate Management > Certificates > Import and import the root certificate.
   - Go to Device > Certificate Management > Certificate Profile > Add.Name the profile and add your imported CA certificate to the list.
3. Add the EDL in PAN-OS
   - Go to Objects > External Dynamic Lists > Add.
   - Type: Select IP, Domain, or URL based on your list.
   - Source: Enter the raw URL of your file.
     - GitHub Example: https://githubusercontent.com
     - Azure DevOps Example: https://azure.com (ensure you use the Raw/Download endpoint)
   - Server Authentication: Check the box to enable server authentication and select the Certificate Profile you created in Step
   - Authentication: Check Authentication, enter your username, and paste your generated PAT as the password.

4. Direct PAN-OS and Edge Management
   - If you're looking for Palo Alto's native platform integrations instead of generic git repositories, you can also natively map to predefined lists using the EDL Hosting Service or manage lists via Cortex Help Center.
