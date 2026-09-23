// @ts-nocheck
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

export type ReminderSchedule = {
  id: string;
  title: string;
  body: string;
  triggerDate: Date;
};

/**
 * Configure notifications for foreground presentation
 */
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

/**
 * Request permissions and schedule a list of reminders.
 * Returns the scheduled reminders for web UI fallback/simulation.
 */
export async function scheduleReminders(
  reminders: ReminderSchedule[]
): Promise<{ success: boolean; scheduled: ReminderSchedule[]; error?: string }> {
  try {
    if (Platform.OS === 'web') {
      // Simulate scheduling for web since native APIs won't work
      return { success: true, scheduled: reminders };
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;
    
    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    
    if (finalStatus !== 'granted') {
      return { success: false, scheduled: [], error: 'Permission not granted' };
    }

    // Cancel previously scheduled EMI notifications if any
    await Notifications.cancelAllScheduledNotificationsAsync();

    const scheduled: ReminderSchedule[] = [];

    for (const reminder of reminders) {
      // Ensure date is in the future
      if (reminder.triggerDate.getTime() > Date.now()) {
        await Notifications.scheduleNotificationAsync({
          content: {
            title: reminder.title,
            body: reminder.body,
            data: { id: reminder.id },
          },
          trigger: { date: reminder.triggerDate },
        });
        scheduled.push(reminder);
      }
    }

    return { success: true, scheduled };
  } catch (error) {
    console.error('Error scheduling notifications:', error);
    return { success: false, scheduled: [], error: String(error) };
  }
}
