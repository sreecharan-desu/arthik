import { Client } from "pg";
import { faker } from "@faker-js/faker";
import * as dotenv from "dotenv";

dotenv.config();

const DATABASE_URL = process.env.DATABASE_URL;

async function seed() {
  if (!DATABASE_URL || DATABASE_URL.includes("sqlite")) {
    console.error(
      "DATABASE_URL must be a Postgres connection string for seed.ts",
    );
    process.exit(1);
  }

  const client = new Client({
    connectionString: DATABASE_URL,
    ssl: DATABASE_URL.includes("neon.tech")
      ? { rejectUnauthorized: false }
      : false,
  });

  try {
    await client.connect();
    console.log("Connected to database for seeding...");

    // 1. Seed Users
    const roles = ["guest", "vendor", "admin"];
    const languages = ["en", "fr", "es", "ko", "hi"];

    process.stdout.write("Seeding Users...");
    for (let i = 0; i < 25; i++) {
      const firstName = faker.person.firstName();
      const lastName = faker.person.lastName();
      const email = faker.internet.email({ firstName, lastName });
      const username = faker.internet.userName({ firstName, lastName });
      const role =
        i === 0 ? "admin" : roles[Math.floor(Math.random() * roles.length)];
      const lang = languages[Math.floor(Math.random() * languages.length)];

      await client.query(
        `
                INSERT INTO users (email, username, first_name, last_name, hashed_password, role, preferred_language, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (email) DO NOTHING
            `,
        [
          email,
          username,
          firstName,
          lastName,
          "hashed_placeholder",
          role,
          lang,
          true,
        ],
      );
      if (i % 5 === 0) process.stdout.write(".");
    }
    console.log(" Done.");

    // 2. Seed Local Providers
    process.stdout.write("Seeding Providers...");
    const cities = ["Hyderabad", "Bengaluru", "Goa", "Jaipur"];
    const providerIds: number[] = [];
    for (let i = 0; i < 12; i++) {
      const name = faker.company.name() + " Tours";
      const city = cities[Math.floor(Math.random() * cities.length)];
      const res = await client.query(
        `
                INSERT INTO local_providers (name, city, phone, email)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            `,
        [name, city, faker.phone.number(), faker.internet.email()],
      );
      providerIds.push(res.rows[0].id);
      process.stdout.write(".");
    }
    console.log(" Done.");

    // 3. Seed Services
    const serviceTypes = ["TOUR", "TRANSPORT"];
    const tagsPool = [
      "family",
      "adventure",
      "heritage",
      "luxury",
      "budget",
      "outdoor",
    ];
    const serviceIds: number[] = [];
    process.stdout.write("Seeding Services...");
    for (let i = 0; i < 60; i++) {
      const providerId =
        providerIds[Math.floor(Math.random() * providerIds.length)];
      const type =
        serviceTypes[Math.floor(Math.random() * serviceTypes.length)];
      const name =
        type === "TOUR"
          ? faker.commerce.productName() + " Safari"
          : "Private " + faker.vehicle.type() + " Transfer";
      const price = parseFloat(faker.commerce.price({ min: 300, max: 6000 }));
      const duration = faker.number.int({ min: 60, max: 480 });
      const tags = JSON.stringify(
        faker.helpers.arrayElements(tagsPool, { min: 1, max: 3 }),
      );

      const res = await client.query(
        `
                INSERT INTO services (provider_id, type, name, description, price, duration, tags, is_available, rating, location)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
            `,
        [
          providerId,
          type,
          name,
          faker.lorem.sentence(),
          price,
          duration,
          tags,
          true,
          (Math.random() * 2 + 3).toFixed(1),
          cities[Math.floor(Math.random() * cities.length)],
        ],
      );
      serviceIds.push(res.rows[0].id);
      if (i % 10 === 0) process.stdout.write(".");
    }
    console.log(" Done.");

    // 4. Seed Bookings
    const userRes = await client.query("SELECT id FROM users LIMIT 25");
    const userIds = userRes.rows.map((r) => r.id);

    process.stdout.write("Seeding Bookings...");
    for (let i = 0; i < 30; i++) {
      const userId = userIds[Math.floor(Math.random() * userIds.length)];
      const serviceId =
        serviceIds[Math.floor(Math.random() * serviceIds.length)];
      const status = faker.helpers.arrayElement([
        "PENDING",
        "CONFIRMED",
        "CANCELLED",
      ]);
      const bookingDate = faker.date.future();
      const amount = 1000.0; // dummy

      await client.query(
        `
                INSERT INTO bookings (user_id, service_id, status, booking_datetime, special_requests, amount, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
            `,
        [userId, serviceId, status, bookingDate, faker.lorem.words(5), amount],
      );
      if (i % 5 === 0) process.stdout.write(".");
    }
    console.log(" Done.");

    // Summary
    console.table({
      users: 25,
      providers: 12,
      services: 60,
      bookings: 30,
    });

    console.log("Seeding completed successfully!");

    // Example curl for webhook test
    const lastBooking = await client.query(
      "SELECT id, payment_id FROM bookings WHERE status = 'PENDING' LIMIT 1",
    );
    if (lastBooking.rows.length > 0) {
      const b = lastBooking.rows[0];
      console.log(
        "\nTo test PayU webhook, use this command (after setting correct signature):",
      );
      console.log(
        `curl -X POST http://localhost:8000/payment/webhook -d "txnid=${b.payment_id}&status=success&hash=YOUR_GENERATED_HASH"`,
      );
    }
  } catch (err) {
    console.error("Seeding error:", err);
  } finally {
    await client.end();
  }
}

seed();
