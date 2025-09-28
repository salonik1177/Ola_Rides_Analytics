# Queries 

-- 1. Retrieve all successful bookings
SELECT *
FROM rides
WHERE booking_status = 'Success';

-- 2. Find the average ride distance for each vehicle type
SELECT vehicle_type,
       ROUND(AVG(ride_distance), 2) AS avg_distance
FROM rides
GROUP BY vehicle_type
ORDER BY avg_distance DESC;

-- 3. Get the total number of rides cancelled by customers
SELECT COUNT(*) AS cancelled_by_customers
FROM rides
WHERE booking_status = 'Canceled by Customer';


-- 4. Find the top 5 customers who booked the highest number of rides
SELECT customer_id,
       COUNT(*) AS ride_count
FROM rides
GROUP BY customer_id
ORDER BY ride_count DESC
LIMIT 5;

-- 5. Calculate the number of rides cancelled by drivers due to personal or car issues
SELECT COUNT(*) AS driver_cancel_personal_car
FROM rides
WHERE booking_status = 'Canceled by Driver'
  AND cancelled_by_driver_reason LIKE '%Personal & Car related issue%';

-- 6. Find the maximum and minimum driver ratings for Prime Sedan bookings
SELECT MAX(driver_rating) AS max_rating,
       MIN(driver_rating) AS min_rating
FROM rides
WHERE vehicle_type = 'Prime Sedan'
  AND driver_rating IS NOT NULL;

-- 7. Retrieve all rides where payment was made using UPI
SELECT *
FROM rides
WHERE payment_method = 'UPI';

-- 8. Calculate the average customer rating for each vehicle type
SELECT vehicle_type,
       ROUND(AVG(customer_rating), 2) AS avg_customer_rating
FROM rides
WHERE customer_rating IS NOT NULL
GROUP BY vehicle_type
ORDER BY avg_customer_rating DESC;

-- 9. Find the total booking value of rides completed successfully
SELECT SUM(booking_value) AS total_success_booking_value
FROM rides
WHERE booking_status = 'Success';


-- 10. List all incomplete rides along with the reason
SELECT booking_id,
       customer_id,
       booking_time,
       incomplete_flag,
       incomplete_reason
FROM rides
WHERE incomplete_flag = 'Yes' OR incomplete_reason IS NOT NULL;