Build a React-based healthcare website called "Health Plus" that allows users to connect with doctors and schedule appointments.

## Project Overview
- Framework: React.js (use Vite for tooling)
- Routing: React Router DOM (v6+)
- Notifications: React-Toastify
- Icons: FontAwesomeIcon (via @fortawesome/react-fontawesome)
- Responsive UI design for seamless user experience across devices.

## Core Features
1. **Home Page:**
   - Hero section with a welcoming message about accessible healthcare.
   - Showcase of services (e.g., "Expert Doctors", "Virtual Consultations").
   - Call-to-action button to book an appointment.

2. **Appointment Booking:**
   - A form to schedule an appointment with a specialist.
   - Fields: Name, Email, Date, Time, and a dropdown to select a Doctor/Specialist.
   - Upon successful submission, show a success notification using React-Toastify.

3. **Virtual Consultation Section:**
   - A page or section explaining how virtual consultations work.
   - Button to "Start Consultation" (can be a placeholder).

4. **Navigation:**
   - A Navbar with links to Home, Appointments, and Consultations.
   - Use React Router DOM to navigate between pages without reloading.

## Technical Constraints
- Use functional components and hooks only.
- Ensure `npm install`, `npm run build`, and `npm test` pass.
- Write your own basic tests using Vitest and React Testing Library.
- DO NOT use TypeScript.

## Required data-testid attributes (CRITICAL for grading)
You MUST include these exact `data-testid` attributes in your components:
- `navbar-home`: Link to home page in Navbar
- `navbar-appointments`: Link to appointments page
- `home-hero`: The main hero section on home page
- `book-btn`: Call-to-action button to book appointment
- `appointment-form`: The form element for booking
- `input-name`: Name input field
- `input-email`: Email input field
- `input-date`: Date input field
- `input-doctor`: Doctor selection dropdown
- `submit-appointment`: Submit button for the form
- `toast-success`: The success notification element (from React-Toastify)
- `consultation-section`: The section explaining virtual consultations

Write the complete project. Ensure all dependencies are listed in `package.json`.