# Build Health Plus - A React Healthcare Website
Build a React-based healthcare website called **"Health Plus"** that allows users to connect with expert doctors, schedule appointments, and receive expert medical advice.

---

## Project Overview
- **Website name:** Health Plus
- **Framework:** React.js (use Vite for tooling)
- **Routing:** React Router DOM (v6+)
- **Notifications:** React-Toastify
- **Icons:** FontAwesomeIcon (via `@fortawesome/react-fontawesome`)
- **Design:** Responsive UI design for seamless user experience across devices.

---

## Core Features (based on README Screenshots)

### 1. Home Page
The Home Page must contain the following sections, in this order:
- **Hero Section:** Welcoming headline about accessible healthcare and a call-to-action button to book an appointment.
- **Information Section:** Short highlights of the services (e.g., "Expert Doctors", "Virtual Consultations").
- **About Section:** Short introduction about Health Plus.
- **Why Choose Health Plus?:** A list of key benefits.
- **Reviews Section:** User reviews (use mock data).
- **Doctors Section:** Cards showing doctors with name and specialty (use mock data).
- **Footer Section:** Navigation links, contact info, and a link to the Legal Documents page.

### 2. Legal Documents Page
- A separate page (route) showing legal documents such as Terms & Conditions and Privacy Policy.

### 3. Appointment Form Page
- A form to schedule an appointment with a specialist.
- **Fields:** Name, Email, Date, Time, and a dropdown to select a Doctor/Specialist.
- **Behavior:** Upon successful submission, show a success notification using React-Toastify.

### 4. Navigation
- A Navbar with links to **Home**, **Appointments**, and **Legal Documents**.
- Use React Router DOM to navigate between pages without reloading.

---

## Technical Constraints
- Use functional components and hooks only.
- **Ensure the code is fully runnable and can be built successfully.** All imports must resolve correctly, and there should be no missing dependencies or syntax errors.
- Ensure `npm install`, `npm run build`, and `npm test` pass flawlessly.
- Write your own basic tests using Vitest and React Testing Library.
- **DO NOT use TypeScript.**

---

## Required `data-testid` Attributes (CRITICAL for grading)
You **MUST** include these exact `data-testid` attributes in your components:

- `navbar-home`: Link to home page in Navbar
- `navbar-appointments`: Link to appointments page
- `navbar-legal`: Link to legal documents page
- `home-hero`: The Hero section on home page
- `home-information`: The Information section
- `home-about`: The About section
- `home-why-choose`: The "Why Choose Health Plus?" section
- `home-reviews`: The Reviews section
- `home-doctors`: The Doctors section
- `footer`: The Footer section
- `book-btn`: Call-to-action button to book appointment
- `legal-page`: The main container of the Legal Documents page
- `appointment-form`: The form element for booking
- `input-name`: Name input field
- `input-email`: Email input field
- `input-date`: Date input field
- `input-time`: Time input field
- `input-doctor`: Doctor selection dropdown
- `submit-appointment`: Submit button for the form
- `toast-success`: The success notification element (from React-Toastify)

Write the complete project. Ensure all dependencies are listed in `package.json`.