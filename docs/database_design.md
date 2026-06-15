# Database Design

The database is centered on the classroom session.

## Academic Tables

- `teachers`: instructors assigned to weekly schedules.
- `subjects`: subjects taught in class.
- `class_groups`: student class groups.
- `students`: individual students.
- `enrollments`: links students to class groups.

## Scheduling Tables

- `weekly_schedules`: defines recurring lessons using teacher, subject, class group, day, time, and room.
- `sessions`: generated class meetings for a specific date from a weekly schedule.

## Monitoring Tables

- `attendance`: student attendance records for a session.
- `ai_events`: detected classroom events for a session.
- `devices`: IoT or camera device status by room.

## Relationship Flow

Teacher + Subject + Class + Day + Time + Room creates a `WeeklySchedule`.

Each `WeeklySchedule` can generate many `Session` records.

Each `Session` can have many `Attendance` records and many `AIEvent` records.

Reports are generated from session attendance and AI event data.
