"""
Media extraction utilities for Meta AI API responses.
"""

from typing import Dict, List


class MediaExtractor:
    """Handles extraction of media content from API responses."""

    @staticmethod
    def extract_media(bot_response_message: Dict) -> List[Dict]:
        """
        Extract media from a bot response message.

        Args:
            bot_response_message: The bot response message dictionary

        Returns:
            List of dictionaries containing extracted media information
        """
        medias = []
        
        imagine_card = bot_response_message.get("imagine_card", {})
        if not imagine_card:
            return medias

        session = imagine_card.get("session", {})
        if not session:
            return medias

        media_sets = session.get("media_sets", [])
        
        for media_set in media_sets:
            imagine_media = media_set.get("imagine_media", [])
            
            for media in imagine_media:
                media_info = {
                    "url": media.get("uri"),
                    "type": media.get("media_type"),
                    "prompt": media.get("prompt"),
                }
                
                # Only add media with valid URL
                if media_info["url"]:
                    medias.append(media_info)

        return medias

    @staticmethod
    def extract_media_urls(bot_response_message: Dict) -> List[str]:
        """
        Extract only the URLs from media in a bot response message.

        Args:
            bot_response_message: The bot response message dictionary

        Returns:
            List of media URLs
        """
        media_list = MediaExtractor.extract_media(bot_response_message)
        return [media["url"] for media in media_list if media.get("url")]

    @staticmethod
    def has_media(bot_response_message: Dict) -> bool:
        """
        Check if the bot response message contains any media.

        Args:
            bot_response_message: The bot response message dictionary

        Returns:
            True if media is present, False otherwise
        """
        imagine_card = bot_response_message.get("imagine_card", {})
        if not imagine_card:
            return False

        session = imagine_card.get("session", {})
        if not session:
            return False

        media_sets = session.get("media_sets", [])
        return len(media_sets) > 0 and any(
            media_set.get("imagine_media", []) for media_set in media_sets
        )