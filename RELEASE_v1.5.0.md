# Dr Magu CLI v1.5.0

## Conversational Command Router

v1.5.0 allows Dr Magu to convert natural-language prompts into explicit commands.

### Added

- ConversationalCommandRouter
- RoutedCommand model
- `router.route`
- `router.execute`
- `dr-magu route`
- `dr-magu route-execute`
- Brain integration for routed commands

### Examples

```bash
dr-magu route "Analyze hubspot.com"
dr-magu route "Analyze repository https://github.com/microsoft/vscode"
dr-magu route "Research the top 10 CRM systems"
```

### Goal

Users no longer need to know internal command names such as `website.analyze`, `repository.read`, or `research.search`.
