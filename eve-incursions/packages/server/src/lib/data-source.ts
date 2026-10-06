import { DataSource } from "typeorm"

export const AppDataSource = new DataSource({
  type: "mysql",
  host: process.env.MYSQL_HOST,
  username: process.env.MYSQL_USER,
  database:  process.env.MYSQL_DB,
  password:  process.env.MYSQL_PASSWORD,
  synchronize: false,
  logging: false,
  entities: [__dirname + "/../models/*.ts"],
  migrations: [],
  subscribers: [],
})
