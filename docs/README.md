
# Team Diamonds

### Team Members:
* Subhradeep Acharjee  
* Ethan Bell 
* Shubham Tanwar  
* Tanya Thomas  
* Conor Zhang   


### Overview:

This project is an AI assistant designed to help people manage their tasks and to-dos from a variety of sources in one place. Rather than switching between tools, the assistant connects to the platforms people already use and provides a unified interface for managing work.

The project is being built incrementally. The first integration is issue trackers (starting with Jira), with plans to expand to email, messaging, and code reviews over time.

### Motivation:

Modern work is spread across many tools — issue trackers, inboxes, chat apps, pull requests. Keeping track of everything requires constant context switching. This assistant aims to bring those sources together so that managing your work feels seamless, regardless of which platforms your team uses.

### Repository Structure:

```

├── components/
│   ├── work_mgmt_client_interface/   # Vendor-neutral interface contracts
│   │   ├── src/
│   │   ├── tests/
│   │   └── README.md
│   │
│   └── jira_client_impl/             # Jira implementation of the interface
│       ├── src/
│       ├── tests/
│       └── README.md
│
├── DESIGN.md                         # Architecture and design decisions
├── CONTRIBUTING.md                   # Contribution guide and rules
└── README.md                         # This file
```

Each component has its own README with setup instructions, usage examples, and test commands.

### How it Works:

The project is split into two layers:

**Interface layer** defines a common contract for what a client must be able to do — fetch issues, create them, update them, delete them — without being tied to any specific platform.

**Implementation layer** fulfills that contract for a specific platform. Today that is Jira. Each implementation is a self-contained package that can be swapped out without changing any of the application code that depends on the interface.

This design means adding a new integration (Linear, GitHub Issues, Gmail, Slack, etc.) only requires writing a new implementation package — the rest of the system stays the same.

### For More Information:

See `DESIGN.md` for a more detailed breakdown of the architecture and the reasoning behind key decisions.
See `CONTRIBUTING.md` for inrformation about how to contribute to the project. 

