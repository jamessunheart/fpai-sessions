import { useEffect, useRef } from 'react';
import { useNotifications } from '../contexts/NotificationContext';
import { api } from '../../lib/api';
import { Sprint } from '../../types';

export function useAutoNotifications() {
  const { addNotification, notifications, isLoaded } = useNotifications();
  const previousSprintsRef = useRef<Sprint[]>([]);

  // Helper function to check if notification already exists
  const notificationExists = (type: string, sprintId: string, status?: string) => {
    return notifications.some(n => 
      n.type === type && 
      n.data?.id === sprintId && 
      (status ? n.data?.fields?.Status === status : true)
    );
  };

  useEffect(() => {
    if (!isLoaded) return; // Wait for localStorage to load
    
    const checkForChanges = async () => {
      try {
        const response = await api.getSprints();
        const currentSprints = response.records || [];
        const previousSprints = previousSprintsRef.current;

        // On first load, check for recent sprints (last 24 hours)
        if (previousSprints.length === 0) {
          const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
          console.log('Checking for recent sprints since:', oneDayAgo);
          
          currentSprints.forEach(sprint => {
            const createdTime = new Date(sprint.createdTime);
            console.log(`Sprint ${sprint.fields.Sprint_ID}: created ${createdTime}, status: ${sprint.fields.Status}`);
            
            // Show notifications for recently completed sprints
            if (sprint.fields.Status === 'Done' && createdTime > oneDayAgo && 
                !notificationExists('proof', sprint.id, 'Done')) {
              console.log('Adding completed sprint notification:', sprint.fields.Sprint_ID);
              addNotification({
                type: 'proof',
                title: 'Sprint Completed',
                message: `${sprint.fields.Name || sprint.fields.Sprint_ID} completed by ${sprint.fields.Dev_Name}`,
                data: { ...sprint, eventTime: createdTime }
              });
            }
            
            // Show notifications for recently created sprints
            if (createdTime > oneDayAgo && !notificationExists('success', sprint.id)) {
              console.log('Adding new sprint notification:', sprint.fields.Sprint_ID);
              addNotification({
                type: 'success',
                title: 'New Sprint Created',
                message: `${sprint.fields.Name || sprint.fields.Sprint_ID} assigned to ${sprint.fields.Dev_Name}`,
                data: { ...sprint, eventTime: createdTime }
              });
            }
          });
        } else {
          // Normal change detection for real-time updates
          currentSprints.forEach(current => {
            const previous = previousSprints.find(p => p.id === current.id);
            
            if (previous && previous.fields.Status !== current.fields.Status && 
                current.fields.Status === 'Done' && !notificationExists('proof', current.id, 'Done')) {
              addNotification({
                type: 'proof',
                title: 'Sprint Completed',
                message: `${current.fields.Name || current.fields.Sprint_ID} completed by ${current.fields.Dev_Name}`,
                data: { ...current, eventTime: new Date() }
              });
            }
          });

          // Check for new sprints
          const newSprints = currentSprints.filter(
            current => !previousSprints.find(p => p.id === current.id)
          );

          newSprints.forEach(sprint => {
            if (!notificationExists('success', sprint.id)) {
              console.log('Adding real-time new sprint notification:', sprint.fields.Sprint_ID);
              addNotification({
                type: 'success',
                title: 'New Sprint Created',
                message: `${sprint.fields.Name || sprint.fields.Sprint_ID} assigned to ${sprint.fields.Dev_Name}`,
                data: { ...sprint, eventTime: new Date(sprint.createdTime) }
              });
            }
          });
        }

        previousSprintsRef.current = currentSprints;
        
        // Check for heartbeat notifications
        try {
          const heartbeatResponse = await fetch('/api/heartbeat-webhook');
          if (heartbeatResponse.ok) {
            const heartbeatData = await heartbeatResponse.json();
            heartbeatData.notifications?.forEach((notification: any) => {
              if (!notification.read) {
                addNotification({
                  type: notification.type,
                  title: notification.title,
                  message: notification.message,
                  data: notification.data
                });
              }
            });
          }
        } catch (error) {
          // Heartbeat notifications not available
        }
      } catch (error) {
        console.error('Auto-notification check failed:', error);
      }
    };

    // Check immediately, then every 10 seconds
    checkForChanges();
    const interval = setInterval(checkForChanges, 10000);

    return () => clearInterval(interval);
  }, [addNotification, notifications, isLoaded]);
}