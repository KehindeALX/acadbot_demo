from rest_framework import serializers


class GuideMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['user', 'assistant'])
    content = serializers.CharField(max_length=1000, trim_whitespace=True, allow_blank=False)


class GuideChatSerializer(serializers.Serializer):
    messages = serializers.ListField(
        child=GuideMessageSerializer(),
        allow_empty=False,
    )

    def validate_messages(self, value):
        if len(value) > 10:
            raise serializers.ValidationError('Send at most the last 10 messages.')
        if value[-1]['role'] != 'user':
            raise serializers.ValidationError('The last message must be from the user.')
        return value
