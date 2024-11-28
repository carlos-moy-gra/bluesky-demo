# Author: Carlos Moyano

import argparse
import requests
import numpy as np
import matplotlib.pyplot as plt

from atproto import Client
from textblob import TextBlob
from bertopic import BERTopic
from decouple import config

def analyze_sentiment(post_text_l):
    """
    Uses TextBlob to perform basic sentiment analysis using predefined rules.
    The sentiment function in TextBlob returns a sentiment tuple of the form
    (polarity, subjectivity). We are interested in polarity, which takes values
    in the range [-1.0, 1.0]. Negative values close to -1 indicate negativity
    and positive values close to 1 indicate positivity.

    Args:
        post_text_l (List[str]): List of posts represented as strings.

    Returns:
        sentiment_counts (Dict[str,int]): Dictionary containing a count of positive,
        neutral and negative posts.
    """
    sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
    positive_post_text_l, neutral_post_text_l, negative_post_text_l, positive_post_score_l, negative_post_score_l = [], [], [], [], []
    for text in post_text_l:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # Range [-1.0, 1.0]
        if polarity > 0:
            sentiment_counts["positive"] += 1
            positive_post_text_l.append(text)
            positive_post_score_l.append(polarity)
        elif polarity < 0:
            sentiment_counts["negative"] += 1
            negative_post_text_l.append(text)
            negative_post_score_l.append(polarity)
        else:
            sentiment_counts["neutral"] += 1
            neutral_post_text_l.append(text)

    positive_posts_text_arr =  np.array(positive_post_text_l)
    positive_posts_score_arr =  np.array(positive_post_score_l)
    positive_posts_text_arr_sort_idx = np.argsort(positive_posts_score_arr)

    negative_posts_text_arr =  np.array(negative_post_text_l)
    negative_posts_score_arr =  np.array(negative_post_score_l)
    negative_posts_text_arr_sort_idx = np.argsort(negative_posts_score_arr)

    print(f"\nMost positive post text: {positive_posts_text_arr[positive_posts_text_arr_sort_idx][1].replace("\n", "").replace(".", ". ")}\n")
    print(f"Most negative post text: {negative_posts_text_arr[negative_posts_text_arr_sort_idx][0].replace("\n", "").replace(".", ". ")}\n")
    print(f"Example neutral post text: {neutral_post_text_l[0].rstrip()}\n")
    
    return sentiment_counts


def plot_sentiment(sentiment_counts):
    """
    Plots the result of the sentiment analysis which consists
    in a count of posts falling into 3 categories: positive,
    negative and neutral.

    Args:
        sentiment_counts (Dict[str,int]): Dictionary containing a count of positive,
        neutral and negative posts.
    """
    categories = list(sentiment_counts.keys())
    counts = list(sentiment_counts.values())
    plt.bar(categories, counts, color=["green", "gray", "red"])
    plt.title("Sentiment Analysis of Last 100 Posts")
    plt.xlabel("Sentiment")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig("sentiment_count.png", dpi=1000)


def perform_sentiment_analysis_of_last_100_posts_from_target_did(client, target_did):
    """
    Performs sentiment analysis of the last 100 post belonging to a target DID from
    Bluesky. After performing sentiment analysis using TextBlob, it plots  as a barplot
    the count of posts falling into the following 3 categories: positive, negative and
    neutral.

    Args:
        client (atproto.Client) : Object representing an AT Protocol client.
        target_did        (str) : String representing a DID, which are persistent, long-term
        identifiers for every account coming from the AT Protocol.
        (link: https://docs.bsky.app/docs/advanced-guides/resolving-identities)
    """
    # 1. Get last 100 posts from target did
    data = client.get_author_feed(
        actor=target_did
        , filter="posts_and_author_threads"
        , limit=100
    )
    posts = data.feed
    post_text_l = list(map(lambda x : x["post"]["record"]["text"], posts))

    # 2. Analyze sentiment of the posts
    sentiment_counts = analyze_sentiment(post_text_l)
    print(f"Sentiment Counts: {sentiment_counts}\n")

    # 3. Plot sentiment buckets
    plot_sentiment(sentiment_counts)


def plot_top_5_topics(topic_counts):
    """
    Plots a summary of the result of topic modeling which consists
    in a count of posts falling into the top 5 topics.

    Args:
        sentiment_counts (Dict[str,int]): Dictionary containing a count of positive,
        neutral and negative posts.
    """
    categories = list(topic_counts.keys())
    counts = list(topic_counts.values())
    plt.bar(categories, counts)
    plt.title("Top 5 Topics Count")
    plt.xlabel("Topic")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig("top_5_topics_count.png", dpi=1000)


def perform_topic_modeling_of_all_posts_from_target_did(client, target_did):
    """
    Performs topic modeling over all the posts belonging to a target DID from
    Bluesky. It extracts the topic of each post by means of a Transformer model
    from Hugging Face and counts the occurrences of each distinct topic. Finally,
    it keeps the 5 topics with the highest number of occurences and plots them
    as a barplot.

    Args:
        client (atproto.Client) : Object representing an AT Protocol client.
        target_did        (str) : String representing a DID, which are persistent, long-term
        identifiers for every account coming from the AT Protocol.
        (link: https://docs.bsky.app/docs/advanced-guides/resolving-identities)
    """
    # Load model to perform Topic Modeling
    # Link: https://huggingface.co/MaartenGr/BERTopic_Wikipedia
    topic_model = BERTopic.load("MaartenGr/BERTopic_Wikipedia") 

    # Initialize an empty list to store all posts
    all_posts_l = []

    cursor = None  # Start with no cursor for the first request
    while True:
        response = client.get_author_feed(
            actor=target_did
            , filter="posts_and_author_threads"
            , limit=100
            , cursor=cursor
        )
        posts = response.feed
        all_posts_l.extend(posts)
        
        # Check if there's a next cursor
        cursor = response.cursor
        if not cursor:
            break  # No more pages to fetch

    post_text_l = list(map(lambda x : x["post"]["record"]["text"].replace("\n", "").replace(".", ". "), all_posts_l))
    print(f"Total posts fetched: {len(post_text_l)}")

    topic_l, _ = topic_model.transform(post_text_l)
    topic_name_l = list(map(lambda x : topic_model.topic_labels_[x].split("_")[1], topic_l.tolist()))
    print(f"Number of unique topics: {len(set(topic_name_l))}")

    topic_counts = {}
    for post_topic_name in topic_name_l:
        if post_topic_name in topic_counts.keys():
            topic_counts[post_topic_name] += 1
        else:
            if post_topic_name not in ["subreddit"]:
                topic_counts[post_topic_name] = 1

    # Keep just top 5 topics
    topic_counts = dict(sorted(topic_counts.items(), key = lambda x: x[1], reverse = True)[:5])

    # Plot the top 5 topics
    plot_top_5_topics(topic_counts)


if __name__ == "__main__":

    # Retrieve credentials from env variables
    handle = config("HANDLE")
    password = config("PASSWORD")

    # Create client and login
    client = Client()
    client.login(handle, password)
    target_username = "aoc.bsky.social" # Target profile on Bluesky

    # Get target did from target username
    response = requests.get(f"https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle={target_username}")
    if response.status_code == 200:
        target_did = response.json()["did"]
    else:
        raise Exception(f"Failed to fetch posts: {response.status_code}, {response.text}")
    
    # Create the parser
    parser = argparse.ArgumentParser()

    # Add an argument
    parser.add_argument('--sentiment', action="store_true", help="...")
    parser.add_argument('--topic', action="store_true", help="...")

    # Parse the arguments
    args = parser.parse_args()

    if args.sentiment:
        try:
            perform_sentiment_analysis_of_last_100_posts_from_target_did(client, target_did)
        except Exception as e:
            print(f"Error: {e}")

    elif args.topic:
        try:
            perform_topic_modeling_of_all_posts_from_target_did(client, target_did)
        except Exception as e:
            print(f"Error: {e}")

    else:
        parser.print_help()
        raise Exception("Error: At least one of the options needs to be passed as argument")
