# AI Bot Factory

BotFactory is a project that enables the creation of intelligent assistants through a Telegram bot interface.

## Overview

The project utilizes Docker and Docker Compose for containerization and orchestration of services. It includes several services:

- `factory`: responsible for creating intelligent assistants via the Telegram bot interface.
- `dozzle`: a web-based Docker container log viewer.
- `db`: PostgreSQL database container.
- `pgadmin`: container for PgAdmin, providing a web interface for PostgreSQL.
- `admin-panel`: a service for an admin panel interface.

To run this project locally, make sure you have Docker and Docker Compose installed.
1. Clone the repository:
```bash
git clone https://github.com/nbbrdn/ai-bot-factory.git
```
2. Navigate to the project directory:
```bash
cd your-repository
```
3. Create a `.env` file based on the provided `.env.example` and set the required environment variables.
4. Start the services using Docker Compose:
```bash
docker-compose up -d
```
5. Access the services:
    - BotFactory Telegram bot: Use the Telegram bot interface to create intelligent assistants.
    - Dozzle: Access at http://localhost:8080 to view Docker container logs.
    - PgAdmin: Access at http://localhost:5050 for the PgAdmin web interface.
    - Admin Panel: Access at http://localhost:5000 for the admin panel interface.

## Structure
- `factory`: responsible for creating intelligent assistants via the Telegram bot interface.
- `dozzle`: a web-based Docker container log viewer.
- `db`: PostgreSQL database container.
- `pgadmin`: container for PgAdmin, providing a web interface for PostgreSQL.
- `admin-panel`: a service for an admin panel interface.

## Contributing
Feel free to contribute to this project by forking the repository and creating pull requests. Any improvements or new features are welcome!

## License
This project is licensed under the MIT License.