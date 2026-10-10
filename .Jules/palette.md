## 2024-10-10 - [Spacer Images Accessibility]
**Learning:** When using empty `<img>` tags as spacers in Markdown profiles (because CSS spacing is unavailable), screen readers might announce them confusingly. Using `alt="" aria-hidden="true"` hides these purely decorative spacers from assistive technologies, improving the reading experience.
**Action:** Always add `alt="" aria-hidden="true"` to structural/spacer images in environments where semantic spacing options are limited.
