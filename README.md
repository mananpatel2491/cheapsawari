# 🚗💨🛫 cheapsawari - Air Flight Booking Tracker

A personal, AI-powered flight tracking dashboard designed to identify the "sweet spot" for booking and alert you when airlines reopen cheaper fare buckets. This app moves away from travel myths and focuses on **Yield Management** data to save money.

## 🧠 The Logic
Airlines use **Fare Buckets** (invisible classes like Q, H, or M) to manage inventory. Prices jump not because of your cookies, but because cheaper buckets sell out in real-time as inventory is depleted. This app tracks those buckets to help you book when inventory is released or demand underperforms forecasts.

### Core Strategies Built-In:
*   **Optimal Booking Windows:** Highlighting the **6–10 week** window for domestic and **8–12 week** window for international flights.
*   **Midweek Travel:** Prioritizing **Tuesday and Wednesday** departures where volume is lowest.
*   **Bucket Reopening Alerts:** Monitoring for sudden price drops (e.g., >15% below the 7-day moving average) that signal an airline has reopened a lower-priced fare class.

## ✨ Key Features
*   **"Sweet Spot" Intent Planner:** A visual calendar that shades your optimal booking velocity windows in green.
*   **Yield Tracker Dashboard:** A table showing actively tracked routes with a **"Bucket Reopened"** badge that triggers when prices drop significantly below the moving average.
*   **Midweek Discount Flags:** Visual indicators for the cheapest days to fly within your target range.
*   **Multi-Channel Alerts:** Integration with **Discord, Slack, or Telegram** webhooks to ping you the moment a deal is detected.

## 🛠️ Tech Stack
This project is built for maximum "vibe coding" efficiency using the Google Gemini ecosystem:

*   **Frontend:** **React** (Vite) + **Tailwind CSS** + **shadcn/ui** for a responsive dashboard.
*   **Backend:** Lightweight **Node.js** or **Python** cron jobs to fetch data silently.
*   **AI Engine:** **Gemini Flash** (Free Tier) used for analyzing pricing trends and generating smart alert payloads.
*   **Data Layer:** **Amadeus Self-Service API** or **FlightClaw** for raw airline pricing data.
*   **Development Tools:** **Google AI Studio** (Vibe Code mode) and **Firebase Studio**.

## 🚀 Getting Started

### 1. Visual Scaffolding
Use the **Vibe Code / Build mode in Google AI Studio** to generate the frontend. You can prompt Gemini to build the interactive calendar and yield tracking charts without writing boilerplate CSS.

### 2. API Configuration
*   Obtain a free **Amadeus Developer API** key. Free quotas are per-API and vary (~200–10k calls/month; confirm yours in the Amadeus Workspace); the test environment serves limited/cached data.
*   Get a **Gemini API Key** from Google AI Studio to handle the "cognitive" analysis of price drops.

### 3. Deployment
The app can be hosted for free on the **Google Cloud Starter Tier** via Firebase App Hosting, requiring no credit card for personal-scale use.

## 📈 Future Expansion
Because this is built on **React**, it is designed to be extensible. Future iterations could include:
*   Interactive trip bundling.
*   Drag-and-drop itinerary builders.
*   Multi-select price comparison matrices.

---
*Built by a Product Manager who knows that timing and flexibility beat clearing cookies every time.*